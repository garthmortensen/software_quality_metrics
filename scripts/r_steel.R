rm(list = ls())

# import helper functions
source("functions/setup_env.R")
source("functions/data_handling.R")
source("functions/stats.R")

CURRENT_MODEL <- "steel"

# handle database and required library configurations
env_settings <- yaml::read_yaml("./data/config.yaml")
setup_env(env_settings$libraries)
con_costs_db <- connect_to_database(env_settings$database$con_costs_db)

# import parameters regarding coordinated group run
coord_filename <- "./data/coordinated/coordinated_data.json"
coord_data <- jsonlite::fromJSON(coord_filename)
# solo or grouped impacts how we source effective timestamps from json or db
solo_or_group <- coord_data$execution_type
print(glue::glue("this model is: {solo_or_group}"))

# import parameters specific to model
json_filename <- glue::glue("./data/input/{CURRENT_MODEL}.json")
json_data <- jsonlite::fromJSON(json_filename)

dependent_variable <- json_data$model_params$dependent_variable

# if upstream in json, must update df_projection with newly generated column
upstream <- "upstream" %in% names(json_data$input)
print(glue::glue("this model has upstream: {upstream}"))

estimate_coefficients <- json_data$model_params$estimate_coefficients
print(glue::glue("json setup to estimate_coefficients: {estimate_coefficients}"))

predict_values <- json_data$model_params$predict_values
print(glue::glue("json setup to predict_values: {predict_values}."))

# get historical info from json
input_hist_table <- pluck(json_data, "input", "historical", "table")
input_hist_effective <- pluck(json_data, "input", "historical", "effective")
df_historical <- get_table_data(con_costs_db, input_hist_table, input_hist_effective)

# get projected info from json
input_proj_table <- pluck(json_data, "input", "projected", "table")
input_proj_effective <- pluck(json_data, "input", "projected", "effective")

if (!upstream) {
  print(glue::glue("!upstream: {!upstream}"))

  effective_projected <- pluck(json_data, "input", "projected", "effective")

  if (solo_or_group == "solo") {
    # source info from json
    effective_predicted <- format(Sys.time(), "%Y%m%d%H%M%S")
  } else if (solo_or_group == "group") {
    # source effective_projected and predicted from db
    print(glue::glue("solo_or_group: {solo_or_group}"))

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
          and whoami = '{whoami}'
          and status = 'queued'
        )
      ")

    # print(query_group_effective)
    df_effective <- dbGetQuery(con_costs_db, query_group_effective)
    print(glue::glue("df_effective: {df_effective}"))
    effective_predicted <- df_effective$effective
    # effective_predicted <- '19991231235959'

    # issue: when you run model which contains upstream data interactively
    # it searched db for upstream effective. instead, source effective from json
    # if (!interactive()) {
    # print("Running via Rscript")
    # effective <- dbGetQuery(con_costs_db, query_group_effective)
    # effective <- effective$effective
    # } else {
    # keep json effective value, since this is not an automated group run
    # print("Running in RStudio")
    # }
  }
  print(glue::glue("effective_projected: {effective_projected}"))
  print(glue::glue("effective_predicted: {effective_predicted}"))

  # lumber only sources effective_projected from json
  # but situationally changes where it sources predictive from, given solo or group
  df_projected <- get_table_data(con_costs_db, input_proj_table, effective_projected)
  print(glue::glue("df_projected: {df_projected}"))
}

# get upstream data
if (upstream) {
  print(glue::glue("upstream: {upstream}"))

  # update df_projected with effective_projected
  input_upstream_model <- pluck(json_data, "input", "upstream", "model")
  input_upstream_table <- pluck(json_data, "input", "upstream", "table")
  input_upstream_attribute <- pluck(json_data, "input", "upstream", "attribute")

  if (solo_or_group == "solo") {
    # source info from json
    print(glue::glue("solo_or_group: {solo_or_group}"))

    effective_projected <- pluck(json_data, "input", "upstream", "effective")
    effective_predicted <- format(Sys.time(), "%Y%m%d%H%M%S")
  } else if (solo_or_group == "group") {
    # source effective_projected and predicted from db
    print(glue::glue("solo_or_group: {solo_or_group}"))

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
          and whoami = '{whoami}'
          and status = 'queued'
        )
      ")

    # print(query_group_effective)

    df_effective <- dbGetQuery(con_costs_db, query_group_effective)
    print(glue::glue("df_effective: {df_effective}"))
    effective_projected <- df_effective$effective
    # effective_projected <- '19991231235959'
    effective_predicted <- effective_projected
  }
  # df_projected <- get_table_data(con_costs_db, input_upstream_table, effective_projected)
  print(glue::glue("effective_projected: {effective_projected}"))
  print(glue::glue("effective_predicted: {effective_predicted}"))

  df_projected <- get_table_data(con_costs_db, input_proj_table, input_proj_effective)
  print(glue::glue("df_projected: {df_projected}"))

  df_upstream <- get_table_data(con_costs_db, input_upstream_table, effective_projected)
  print(glue::glue("df_upstream: {df_upstream}"))

  # replacing column values
  df_projected[[input_upstream_attribute]] <- df_upstream[[input_upstream_attribute]]
  print(glue::glue("df_projected: {df_projected}"))
}

# update df_projected using json provided timestamp
if (upstream && solo_or_group == "solo") {
  print(glue::glue("upstream && solo_or_group: {upstream} && {solo_or_group}"))

  # update df_projected with effective_projected
  df_upstream <- get_table_data(con_costs_db, input_upstream_table, effective_projected)
  print(glue::glue("df_upstream: {df_upstream}"))
  df_projected[[input_upstream_attribute]] <- df_upstream[[input_upstream_attribute]]
  print(glue::glue("df_projected: {df_projected}"))
}


# get historical data and re-estimate model
variables_to_ignore <- c("id", "effective")
if (estimate_coefficients) {
  print(glue::glue("estimate_coefficients: {estimate_coefficients}"))
  model <- estimate(df_historical, dependent_variable, variables_to_ignore)
} else {
  print(glue::glue("estimate_coefficients: {estimate_coefficients}. New estimation coefficients will NOT be produced."))
}

# predict with the RDS model and write results to db with new effective
if (predict_values) {
  print(glue::glue("predict_values: {predict_values}"))

  # get model
  model <- readRDS(glue::glue("./models/{dependent_variable}.rds"))

  # predict and create formatted tibble
  df_predicted <- make_predictions(model, df_projected, dependent_variable) %>%
    mutate(effective = effective_predicted) %>% # update effective timestamp
    mutate(date = format(date, "%Y-%m-%d")) %>% # db format
    select(-id) # drop id column to satisfy unique constraint

  # write values to db and csv, then print for visual check
  output_table <- pluck(json_data, "output", "table")
  dbWriteTable(con_costs_db, output_table, df_predicted, append = TRUE)
  write_to_csv(df_predicted, "./data/output", output_table)
  display_verification(con_costs_db, output_table, dependent_variable, 3)
} else {
  print(glue::glue("predict_values: {predict_values}. New predicted values will NOT be produced."))
}

print(glue::glue("script complete: {CURRENT_MODEL}"))
