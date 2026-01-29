import pandas as pd
import optparse
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.collector import get_pressure_temperature, read_gps_position, get_rtc_datetime, read_luminosity, get_scd30_data
from utils.generator import activate_generator, activate_generator_collected
from utils.writeUtils import write_json
from utils.dataUtils import get_formatted_moods
from utils.loggerUtils import logger, timestamp_str
from datetime import datetime
from storage.sendOracle import upload_to_bucket
from my_secrets.secrets import generated_collected_data_dir


df = pd.DataFrame()


if __name__ == "__main__":
    logger.info("----- Application : developing phase -----")

    parser = optparse.OptionParser()

    # add options
    parser.add_option("-g", "--generator-computed",
                      dest="generator_computed",
                      action="store_true",
                      default=False,
                      help="Activate the data generator mode (default: False)")
    parser.add_option("--generator-collected",
                      dest="generator_collected",
                      default=False,
                      help="Generate data as collected data only.\n On other hand, -g option allows to generate complete test data, after collecting and computing.\n (default: False)")
    parser.add_option("-m", "--moods",
                      dest="moods",
                      action="append",
                      default=[],
                      help="List of moods to filter (can be used multiple times)")
    parser.add_option("-c", "--collected",
                      dest="collected",
                      action="store_true",
                      default=False,
                      help="Collect data only (default: False)")
    parser.add_option("-b", "--bucket",
                      dest="bucket",
                      default=False,
                      help="Upload generated files to Oracle Cloud bucket (default: False)")
    parser.add_option("-z", "--zone-time",
                      dest="zone_time",
                      default="France",
                      help="Zone time for RTC datetime (default: France)")


    (options, args) = parser.parse_args()

    timestamp_begin_job = datetime.now()
    json_object = []

    try:
        if options.generator_computed:
            logger.info("----- Data generator option : computed -----")
            try:
                collected_dir = f'{generated_collected_data_dir}'
                collected_files_data = []
                if os.path.isdir(collected_dir):
                    for file in os.listdir(collected_dir):
                        if file.endswith('.json'):
                            logger.info(f"file found: {file}")
                            path = os.path.join(collected_dir, file)
                            logger.info(f"JSON object before generator: {json_object}")
                            json_object = activate_generator(json_object, file)
                            df = pd.DataFrame(json_object)
                            logger.info(f"DataFrame Pandas created with {len(df)} lines")
                            print(df.head())
                            logger.info("----- Writing generated data in JSON format -----")
                            write_json(json_object, timestamp_str, options, file)

            except Exception as e:
                logger.error(f"Data generator error: {e}")
        elif options.generator_collected:
            logger.info("----- Data generator option : collected -----")
            try:
                json_object = activate_generator_collected(json_object)
                df = pd.DataFrame(json_object)
                logger.info(f"DataFrame Pandas created with {len(df)} lines")
                print(df.head())

            except Exception as e:
                logger.error(f"Data generator error: {e}")
                
        elif options.collected:
            logger.info("----- Data collect mode -----")
            zone_time = options.zone_time if options.zone_time else "France"
            local_timestamp = get_rtc_datetime(zone_time)
            moods = options.moods if options.moods else ["default"]
            mood_dict = get_formatted_moods(moods)
                        
            temperature_bmp280, pressure = get_pressure_temperature()
            co2, temperature_scd30, humidity = get_scd30_data()
            latitude, longitude, altitude = read_gps_position()
            luminosity, white_luminosity = read_luminosity()
            
            row = {
                "local_timestamp": local_timestamp,
                "temperature_bmp280": temperature_bmp280,
                "temperature_scd30": temperature_scd30,
                "luminosity": luminosity,
                "white_luminosity": white_luminosity,
                "pressure": pressure,
                "latitude": latitude,
                "longitude": longitude,
                "altitude_m": altitude,
                "moods": mood_dict
            }
            json_object.append(row)
            logger.info(f"Collected data : {row}")
            logger.info("----- End of data collection mode -----")
            exit(0)

    except Exception as e:
        logger.error(f"General error : {e}")
    finally:
        duree = datetime.now() - timestamp_begin_job
        logger.info(f"Collect duration: {duree}")
            
        if json_object and options.collected and options.moods:
            logger.info("----- Writing collected data in JSON format -----")
            write_json(json_object, timestamp_str, options, None)
        if json_object and not options.generator_computed and options.generator_collected:
            logger.info("----- Writing generated data in JSON format -----")
            write_json(json_object, timestamp_str, options, None)
        if options.bucket and options.generator_computed:
            logger.info("----- Uploading generated files (option -g) to Oracle Cloud bucket -----")
            upload_to_bucket("data/output/generated/environmental_to_send/computed/", "wildtrace-environmental", options)
        if options.bucket and options.generator_collected:
            logger.info("----- Uploading generated files (option -gc) to Oracle Cloud bucket -----")
            upload_to_bucket(f"{generated_collected_data_dir}/", "wildtrace-environmental", options)
        elif options.bucket and not (options.generator_computed or options.generator_collected):
            logger.info("Upload into Oracle Cloud bucket not activated.")
            logger.info("To activate, use the -b or --bucket option, along with one of the generator options.")
