# import helper functions
source("functions/test_function.R")
source("functions/setup_env.R")
source("functions/data_handling.R")
source("functions/stats.R")


print("top level script works")

CURRENT_MODEL <- "energy"

# handle database and required library configurations
env_settings <- yaml::read_yaml("./data/config.yaml")
setup_env(env_settings$libraries)
con_costs_db <- connect_to_database(env_settings$database$con_costs_db)
