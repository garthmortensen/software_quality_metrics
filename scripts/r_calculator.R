rm(list = ls())

# import helper functions
source("functions/setup_env.R")
source("functions/data_handling.R")


CURRENT_MODEL <- "calculator"

# handle database and required library configurations
env_settings <- yaml::read_yaml("./data/config.yaml")
setup_env(env_settings$libraries)
con_costs_db <- connect_to_database(env_settings$database$con_costs_db)

# import parameters regarding coordinated group run
coord_filename <- "./data/coordinated/coordinated_data.json"
coord_data <- jsonlite::fromJSON(coord_filename)
solo_or_group <- coord_data$execution_type
print(glue::glue("this run is: {solo_or_group}"))

# import parameters specific to model
json_filename <- glue::glue("./data/input/{CURRENT_MODEL}.json")
json_data <- jsonlite::fromJSON(json_filename)

calculate <- json_data$model_params$calculate
print(glue::glue("calculate: {calculate}"))
if (calculate) {
  # loop through all tables listed in json
  models <- json_data$model_params$models
  print(glue::glue("models: {models}"))

  # first create an empty df with date and effective timestamp columns
  query_first <- glue::glue("
    select date, effective
    from {models[[1]]}_predicted
    where effective = (select max(effective) from {models[[1]]}_predicted)
    ")
  date_effective_df <- dbGetQuery(con_costs_db, as.character(query_first))
  combined_df <- tibble(date = date_effective_df$date, effective = date_effective_df$effective)

  all_model_columns <- list()

  for (model in models) {
    query <- glue::glue("
     select date, factory_price_{model}
     from {model}_predicted
     where effective = (select max(effective) from {model}_predicted)
     ")
    print(glue::glue("model: {model}"))
    result <- dbGetQuery(con_costs_db, as.character(query))

    factory_price <- result[, 2]
    print(factory_price)
    col_name <- glue::glue("factory_price_{model}")
    print(col_name)

    # tag on the new columns
    combined_df <- add_column(combined_df, !!col_name := factory_price)

    # save for later when creating summation
    all_model_columns <- append(all_model_columns, col_name)
  }

  # sum costs across rows for total annual cost
  summed_columns <- combined_df %>%
    select(!!!all_model_columns) %>%
    rowSums()

  # Combine date column and summed columns into a tibble
  df_calculated <- tibble(date = date_effective_df$date, effective = date_effective_df$effective[1], annual_sum = summed_columns)
  print(df_calculated)

  # output to db and csv, display for verification
  table_output <- json_data$output$table
  dbWriteTable(con_costs_db, table_output, df_calculated, append = TRUE)
  write_to_csv(df_calculated, "./data/output/", table_output)
}
