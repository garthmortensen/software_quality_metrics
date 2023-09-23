rm(list = ls())

# import helper functions
source("functions/setup_env.R")
source("functions/data_handling.R")
source("functions/stats.R")

CURRENT_MODEL <- "energy"

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
dependent_variable <- json_data$model_params$dependent_variable

# generate appropriate effective timestamps for projected data
if (solo_or_group == "solo") {
  effective_projected <- format(Sys.time(), "%Y%m%d%H%M%S")
} else if (solo_or_group == "group") {
  # source effective from db
  whoami <- "dog" # Sys.info()["user"]
  query_group_effective <- glue::glue("
      select
        max(group_id) as max_group_id
        , effective
      from
        (
        select *
        from coordinated
        where model = '{CURRENT_MODEL}'
          and status = 'queued'
          and whoami = '{whoami}'
        )
      ")

  # print(query_group_effective)

  effective_df <- dbGetQuery(con_costs_db, query_group_effective)
  print(glue::glue("effective_df: {effective_df}"))
  effective_projected <- effective_df$effective
  print(glue::glue("effective_projected: {effective_projected}"))
  # effective_projected <- '19991231235959'
}

# generate new data and write to db with new effective
generate <- json_data$model_params$generate
if (generate) {
  print(glue::glue("generate: {json_data$model_params$generate}. Generated output will be produced."))

  # generate date sequence
  date_column <- seq(ymd("2023-07-01"), ymd("2024-01-01"), by = "1 month")
  formatted_dates <- format(date_column, "%Y-%m-%d")

  # generate random data
  # set.seed(123)
  random_values <- runif(7, 10, 100) # obs, min, max

  # create formatted tibble
  df <- tibble(date = formatted_dates, random_values) %>% # use original date index
    rename_with(~dependent_variable, random_values) %>%
    add_column(effective_projected, .after = "date") %>%
    rename(effective = effective_projected)

  # write values to db and csv, then print for visual check
  output_table <- json_data$output$table
  dbWriteTable(con_costs_db, output_table, df, append = TRUE)
  write_to_csv(df, "./data/output/", output_table)
  display_verification(con_costs_db, output_table, dependent_variable, 3)
}

# clear all variables
rm(list = ls())
