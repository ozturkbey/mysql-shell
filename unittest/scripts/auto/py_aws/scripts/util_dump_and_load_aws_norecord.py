#@ {has_aws_environment()}

#@<> INCLUDE aws_utils.inc

#@<> INCLUDE dump_utils.inc

#@<> setup
setup_tests(load_tests = True)

#@<> helpers
def EXPECT_SUCCESS(options = {}, excluded_options = []):
    aws_options = get_options(options, excluded_options)
    print(f"--> EXPECT_SUCCESS -> {aws_options}")
    def dump(method, *args):
        method = "dump_" + method
        print(f"--> Executing util.{method}()")
        setup_session(__sandbox_uri1)
        clean_bucket()
        EXPECT_NO_THROWS(lambda: util[method](*args, dump_dir, aws_options), f"Failed to dump using options: {aws_options}")
    def load():
        print("--> Executing util.load_dump()")
        setup_session(__sandbox_uri2)
        wipeout_server(session)
        EXPECT_NO_THROWS(lambda: util.load_dump(dump_dir, aws_options), f"Failed to load using options: {aws_options}")
    dump("instance")
    load()
    dump("schemas", [ "world" ])
    load()
    dump("tables", "world", [ "Country" ])
    load()

def EXPECT_FAIL(error, msg, options = {}, excluded_options = [], argument_error = True):
    aws_options = get_options(options, excluded_options)
    print(f"--> EXPECT_FAIL -> {aws_options}")
    def full_msg(method, options_arg):
        is_re = is_re_instance(msg)
        m = f"{re.escape(error) if is_re else error}: Util.{method}: {f'Argument #{options_arg}: ' if argument_error else ''}{msg.pattern if is_re else msg}"
        if is_re:
            m = re.compile("^" + m)
        return m
    def dump(method, *args):
        method = "dump_" + method
        print(f"--> Executing util.{method}()")
        setup_session(__sandbox_uri1)
        clean_bucket()
        EXPECT_THROWS(lambda: util[method](*args, dump_dir, aws_options), full_msg(method, 2 + len(args)))
    def load():
        print("--> Executing util.load_dump()")
        setup_session(__sandbox_uri2)
        wipeout_server(session)
        EXPECT_THROWS(lambda: util.load_dump(dump_dir, aws_options), full_msg("load_dump", 2))
    dump("instance")
    dump("schemas", [ "world" ])
    dump("tables", "world", [ "Country" ])
    load()

#@<> WL14387-TSFR_1
help_text = """
      - s3BucketName: string (default: not set) - Name of the AWS S3 bucket to
        use. The bucket must already exist.
      - s3CredentialsFile: string (default: not set) - Use the specified AWS
        credentials file.
      - s3ConfigFile: string (default: not set) - Use the specified AWS config
        file.
      - s3Profile: string (default: not set) - Use the specified AWS profile.
      - s3Region: string (default: not set) - Use the specified AWS region.
      - s3EndpointOverride: string (default: not set) - Use the specified AWS
        S3 API endpoint instead of the default one.
"""

EXPECT_TRUE(help_text in util.help("dump_instance"))
EXPECT_TRUE(help_text in util.help("dump_schemas"))
EXPECT_TRUE(help_text in util.help("dump_tables"))
EXPECT_TRUE(help_text in util.help("load_dump"))

#@<> WL14387-TSFR_1_1_2
EXPECT_SUCCESS()

#@<> WL14387-TSFR_2_1_2
WIPE_SHELL_LOG()
EXPECT_FAIL("RuntimeError", "Could not select the AWS credentials provider, please see log for more details", { "s3Profile": "non-existing-profile" })
EXPECT_SHELL_LOG_CONTAINS(f"Warning: The credentials file at '{MYSQLSH_AWS_SHARED_CREDENTIALS_FILE}' does not contain a profile named: 'non-existing-profile'.")
EXPECT_SHELL_LOG_CONTAINS(f"Warning: The config file at '{MYSQLSH_AWS_CONFIG_FILE}' does not contain a profile named: 'non-existing-profile'.")
EXPECT_SHELL_LOG_CONTAINS("Info: The environment variables are not going to be used to fetch AWS credentials, because the 's3Profile' option is set.")

#@<> WL14387-TSFR_2_1_4
#    WL14387-TSFR_4_2_1
with write_profile(local_aws_config_file, "profile " + local_aws_profile, aws_settings):
    EXPECT_SUCCESS({ "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file })

#@<> WL14387-TSFR_2_1_5
with write_profile(local_aws_config_file, "profile " + local_aws_profile, { "region": aws_settings.get("region", default_aws_region) }):
    with write_profile(local_aws_credentials_file, local_aws_profile, aws_settings):
        EXPECT_SUCCESS({ "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": local_aws_credentials_file })

#@<> WL14387-TSFR_3_1
#    WL14387-TSFR_3_1_2_1
#    WL14387-TSFR_3_2_1
with write_profile(default_aws_config_file, "profile " + local_aws_profile, { "region": aws_settings.get("region", default_aws_region) }):
    with write_profile(default_aws_credentials_file, local_aws_profile, aws_settings):
        # empty strings cause dumper/loader to use files from the default location
        EXPECT_SUCCESS({ "s3Profile": local_aws_profile, "s3ConfigFile": "", "s3CredentialsFile": "" })

#@<> WL14387-TSFR_3_1_1
with write_profile(default_aws_config_file, "profile " + local_aws_profile, { "region": aws_settings.get("region", default_aws_region) }):
    with write_profile(default_aws_credentials_file, local_aws_profile, { "aws_access_key_id": "invalid", "aws_secret_access_key": "invalid" }):
        with write_profile(local_aws_credentials_file, local_aws_profile, aws_settings):
            # empty strings cause dumper/loader to use files from the default location
            EXPECT_SUCCESS({ "s3Profile": local_aws_profile, "s3ConfigFile": "", "s3CredentialsFile": local_aws_credentials_file })

#@<> WL14387-TSFR_3_2_2
current_log_level = shell.options["logLevel"]
shell.options["logLevel"] = 8
aws_session_token = random_string(20)

with write_profile(local_aws_credentials_file, local_aws_profile, { **aws_settings, "aws_session_token": aws_session_token }):
    # token is temporary, so we cannot use a predefined one for our testing, instead we check if the token we set is sent along with the headers
    setup_session(__sandbox_uri1)
    clean_bucket()
    WIPE_SHELL_LOG()
    try:
        util.dump_instance(dump_dir, get_options({ "s3Profile": local_aws_profile, "s3CredentialsFile": local_aws_credentials_file }))
    except Exception as e:
        pass
    EXPECT_SHELL_LOG_CONTAINS(f"'x-amz-security-token' : '{aws_session_token}'")

shell.options["logLevel"] = current_log_level

#@<> WL14387-TSFR_4_1
with write_profile(local_aws_config_file, "profile " + local_aws_profile, {}):
    with write_profile(local_aws_credentials_file, local_aws_profile, {}):
        EXPECT_FAIL("RuntimeError", f"The AWS access and secret keys were not found in: credentials file ({local_aws_credentials_file}), config file ({local_aws_config_file}", { "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": local_aws_credentials_file })

#@<> WL14387-TSFR_4_2
with write_profile(local_aws_config_file, "profile " + local_aws_profile, {}):
    with write_profile(local_aws_credentials_file, local_aws_profile, {}):
        with open(local_aws_config_file, "a") as f:
            f.write("invalid line")
        EXPECT_FAIL("RuntimeError", f"Failed to parse config file '{local_aws_config_file}': expected setting-name=value, in line 3: invalid line", { "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": local_aws_credentials_file })

with write_profile(local_aws_config_file, "profile " + local_aws_profile, {}):
    with write_profile(local_aws_credentials_file, local_aws_profile, {}):
        with open(local_aws_credentials_file, "a") as f:
            f.write("invalid line")
        EXPECT_FAIL("RuntimeError", f"Failed to parse config file '{local_aws_credentials_file}': expected setting-name=value, in line 3: invalid line", { "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": local_aws_credentials_file })

#@<> WL14387-TSFR_4_1_1
with write_profile(default_aws_config_file, "profile " + local_aws_profile, { "aws_access_key_id": "invalid", "aws_secret_access_key": "invalid" }):
    with write_profile(default_aws_credentials_file, local_aws_profile, {}):
        with write_profile(local_aws_config_file, local_aws_profile, aws_settings):
            # empty strings cause dumper/loader to use files from the default location
            EXPECT_SUCCESS({ "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": "" })

#@<> WL14387-TSFR_4_1_2_1
with write_profile(default_aws_config_file, "profile " + local_aws_profile, aws_settings):
    # empty strings cause dumper/loader to use files from the default location
    EXPECT_SUCCESS({ "s3Profile": local_aws_profile, "s3ConfigFile": "", "s3CredentialsFile": "" })

#@<> WL14387-TSFR_4_2_2
current_log_level = shell.options["logLevel"]
shell.options["logLevel"] = 8
aws_session_token = random_string(20)

with write_profile(local_aws_config_file, "profile " + local_aws_profile, { **aws_settings, "aws_session_token": aws_session_token }):
    # token is temporary, so we cannot use a predefined one for our testing, instead we check if the token we set is sent along with the headers
    setup_session(__sandbox_uri1)
    clean_bucket()
    WIPE_SHELL_LOG()
    try:
        util.dump_instance(dump_dir, get_options({ "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file }))
    except Exception as e:
        pass
    EXPECT_SHELL_LOG_CONTAINS(f"'x-amz-security-token' : '{aws_session_token}'")

shell.options["logLevel"] = current_log_level

#@<> WL14387-TSFR_4_2_3
current_log_level = shell.options["logLevel"]
shell.options["logLevel"] = 8
aws_region = random_string(20)

with write_profile(local_aws_config_file, "profile " + local_aws_profile, { **aws_settings, "region": aws_region }):
    # we have a fixed region set in our credentials, in order to test if the region from the config file is used, we check the headers, and don't care about the result
    setup_session(__sandbox_uri1)
    clean_bucket()
    WIPE_SHELL_LOG()
    try:
        util.dump_instance(dump_dir, get_options({ "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file }))
    except Exception as e:
        pass
    EXPECT_SHELL_LOG_CONTAINS(get_scope(aws_region))

shell.options["logLevel"] = current_log_level

#@<> WL14387-TSFR_4_2_1_1
current_log_level = shell.options["logLevel"]
shell.options["logLevel"] = 8
aws_region = random_string(20)

with write_profile(local_aws_config_file, "profile " + local_aws_profile, {}):
    with write_profile(local_aws_credentials_file, local_aws_profile, { **aws_settings, "region": aws_region }):
        # we have a fixed region set in our credentials, in order to test if the default region is used, we check the headers, and don't care about the result
        setup_session(__sandbox_uri1)
        clean_bucket()
        WIPE_SHELL_LOG()
        try:
            util.dump_instance(dump_dir, get_options({ "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": local_aws_credentials_file }))
        except Exception as e:
            pass
        EXPECT_SHELL_LOG_CONTAINS(get_scope("us-east-1"))

shell.options["logLevel"] = current_log_level

#@<> WL14387-TSFR_5_1
# BUG#34604763 - partial credentials are an error
with write_profile(local_aws_config_file, "profile " + local_aws_profile, { "region": aws_settings.get("region", default_aws_region), "aws_access_key_id": aws_settings["aws_access_key_id"] }):
    with write_profile(local_aws_credentials_file, local_aws_profile, { "aws_secret_access_key": aws_settings["aws_secret_access_key"] }):
        EXPECT_FAIL("RuntimeError", f"Partial AWS credentials found in credentials file ({local_aws_credentials_file}), missing the value of 'aws_access_key_id'", { "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": local_aws_credentials_file })

#@<> WL14387-TSFR_5_2
current_log_level = shell.options["logLevel"]
shell.options["logLevel"] = 8
aws_session_token = random_string(20)

with write_profile(local_aws_config_file, "profile " + local_aws_profile, { **aws_settings, "aws_session_token": aws_session_token }):
    with write_profile(local_aws_credentials_file, local_aws_profile, { "region": aws_settings.get("region", default_aws_region), "aws_session_token": "invalid" }):
        # token is temporary, so we cannot use a predefined one for our testing, instead we check if the token we set is sent along with the headers
        setup_session(__sandbox_uri1)
        clean_bucket()
        WIPE_SHELL_LOG()
        try:
            util.dump_instance(dump_dir, get_options({ "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": local_aws_credentials_file }))
        except Exception as e:
            pass
        EXPECT_SHELL_LOG_CONTAINS(f"'x-amz-security-token' : '{aws_session_token}'")

shell.options["logLevel"] = current_log_level

#@<> WL14387-TSFR_5_3
with write_profile(local_aws_config_file, "profile " + local_aws_profile, { "region": aws_settings.get("region", default_aws_region), "aws_access_key_id": "invalid", "aws_secret_access_key": "invalid" }):
    with write_profile(local_aws_credentials_file, local_aws_profile, { "aws_access_key_id": aws_settings["aws_access_key_id"], "aws_secret_access_key": aws_settings["aws_secret_access_key"] }, { "invalid-profile": { "aws_access_key_id": "invalid", "aws_secret_access_key": "invalid" } }):
        EXPECT_SUCCESS({ "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": local_aws_credentials_file })

#@<> WL14387-TSFR_5_1_1
with write_profile(default_aws_config_file, "profile " + local_aws_profile, {}):
    with write_profile(local_aws_credentials_file, local_aws_profile, { "aws_secret_access_key": aws_settings["aws_secret_access_key"] }):
        EXPECT_FAIL("RuntimeError", f"Partial AWS credentials found in credentials file ({local_aws_credentials_file}), missing the value of 'aws_access_key_id'", { "s3Profile": local_aws_profile, "s3ConfigFile": "", "s3CredentialsFile": local_aws_credentials_file })

#@<> WL14387-TSFR_5_2_1
with write_profile(local_aws_config_file, "profile " + local_aws_profile, { "aws_secret_access_key": "", "aws_access_key_id": "invalid" }):
    with write_profile(local_aws_credentials_file, local_aws_profile, {}):
        # aws_access_key_id is invalid, so we're expecting an 403 Forbidden error
        EXPECT_FAIL("Error: Shell Error (54403)", re.compile(".* \(403\)"), { "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": local_aws_credentials_file }, argument_error = False)

#@<> WL14387-TSFR_5_2_2
with write_profile(local_aws_config_file, "profile " + local_aws_profile, { "region": aws_settings.get("region", default_aws_region) }):
    with write_profile(local_aws_credentials_file, local_aws_profile, { "aws_access_key_id": aws_settings["aws_access_key_id"] }):
        EXPECT_FAIL("RuntimeError", f"Partial AWS credentials found in credentials file ({local_aws_credentials_file}), missing the value of 'aws_secret_access_key'", { "s3Profile": local_aws_profile, "s3ConfigFile": "", "s3CredentialsFile": local_aws_credentials_file })

#@<> WL14387-TSFR_5_3_1
current_log_level = shell.options["logLevel"]
shell.options["logLevel"] = 8

with write_profile(local_aws_config_file, "profile " + local_aws_profile, { "region": aws_settings.get("region", default_aws_region), "aws_session_token": "" }):
    with write_profile(local_aws_credentials_file, local_aws_profile, { "aws_access_key_id": aws_settings["aws_access_key_id"], "aws_secret_access_key": aws_settings["aws_secret_access_key"] }):
        WIPE_SHELL_LOG()
        EXPECT_SUCCESS({ "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": local_aws_credentials_file })
        # with empty aws_session_token setting, the x-amz-security-token header should not be used
        EXPECT_SHELL_LOG_NOT_CONTAINS(f"'x-amz-security-token'")

shell.options["logLevel"] = current_log_level

#@<> WL14387-TSFR_6_2_1
current_log_level = shell.options["logLevel"]
shell.options["logLevel"] = 8

with write_profile(local_aws_config_file, "profile " + local_aws_profile, { **aws_settings, "region": default_aws_region }):
    # we're not checking if operation succeeds or not, we're checking if the default endpoint is used
    setup_session(__sandbox_uri1)
    clean_bucket()
    WIPE_SHELL_LOG()
    try:
        util.dump_instance(dump_dir, get_options({ "s3EndpointOverride": "", "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file }))
    except Exception as e:
        pass
    EXPECT_SHELL_LOG_CONTAINS(f"s3.{default_aws_region}.amazonaws.com GET")

shell.options["logLevel"] = current_log_level

#@<> WL14387-TSFR_6_3_1
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

class RejectGet(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def do_GET(self):
        response = "<Error><Message>Access forbidden!</Message></Error>"
        self.send_response(403)
        self.send_header('Content-Type', 'application/xml')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode('ascii'))
        self.close_connection = True
    def log_message(self, format, *args):
        pass

while True:
    http_port = random.randint(50000, 60000)
    if not testutil.is_tcp_port_listening("127.0.0.1", http_port):
        break

http_server = HTTPServer(("127.0.0.1", http_port), RejectGet)
http_thread = threading.Thread(target = http_server.serve_forever)
http_thread.start()

current_log_level = shell.options["logLevel"]
shell.options["logLevel"] = 8

with write_profile(local_aws_config_file, "profile " + local_aws_profile, { **aws_settings, "region": default_aws_region }):
    # operation will fail, because our test server sends 403, we're checking here if the specified endpoint is used
    setup_session(__sandbox_uri1)
    clean_bucket()
    WIPE_SHELL_LOG()
    EXPECT_THROWS(lambda: util.dump_instance(dump_dir, get_options({ "s3EndpointOverride": f"http://127.0.0.1:{http_port}/", "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file })), "Access forbidden! (403)")
    EXPECT_SHELL_LOG_CONTAINS(f"http://127.0.0.1:{http_port} GET")

shell.options["logLevel"] = current_log_level

http_server.shutdown()
http_server.server_close()
http_thread.join()

#@<> WL14387-TSFR_6_3_2
current_log_level = shell.options["logLevel"]
shell.options["logLevel"] = 8

with write_profile(local_aws_config_file, "profile " + local_aws_profile, { **aws_settings, "region": default_aws_region }):
    # we're not checking if operation succeeds or not, we're checking if the default endpoint is used
    setup_session(__sandbox_uri1)
    clean_bucket()
    WIPE_SHELL_LOG()
    try:
        util.dump_instance(dump_dir, get_options({ "s3EndpointOverride": "https://mynamespace.compat.objectstorage.us-phoenix-1.oraclecloud.com", "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file }))
    except Exception as e:
        pass
    EXPECT_SHELL_LOG_CONTAINS("https://mynamespace.compat.objectstorage.us-phoenix-1.oraclecloud.com GET")

shell.options["logLevel"] = current_log_level

#@<> WL14387-TSFR_ET_1
with write_profile(local_aws_config_file, "profile " + local_aws_profile, aws_settings):
    with write_profile(local_aws_credentials_file, local_aws_profile + "-invalid", {}):
        EXPECT_SUCCESS({ "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": local_aws_credentials_file })

#@<> BUG#34599319 - dump&load when paths contain spaces and other characters that need to be URL-encoded
tested_schema = "test schema"
tested_table = "fish & chips"
bug_34599319_dump_dir = "shell test/dump & load"

setup_session(__sandbox_uri1)
session.run_sql("DROP SCHEMA IF EXISTS !;", [ tested_schema ])
session.run_sql("CREATE SCHEMA !;", [ tested_schema ])
session.run_sql("CREATE TABLE !.! (id INT PRIMARY KEY);", [ tested_schema, tested_table ])
session.run_sql("INSERT INTO !.! (id) VALUES (1234);", [ tested_schema, tested_table ])
session.run_sql("ANALYZE TABLE !.!;", [ tested_schema, tested_table ])

aws_options = get_options({ "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file })

# prepare the dump
clean_bucket()

with write_profile(local_aws_config_file, "profile " + local_aws_profile, aws_settings):
    util.dump_schemas([tested_schema], bug_34599319_dump_dir, aws_options)

#@<> BUG#34599319 - test
setup_session(__sandbox_uri2)
wipeout_server(session)

with write_profile(local_aws_config_file, "profile " + local_aws_profile, aws_settings):
    EXPECT_NO_THROWS(lambda: util.load_dump(bug_34599319_dump_dir, aws_options), "load_dump() with URL-encoded file names")

EXPECT_STDOUT_CONTAINS(f"1 tables in 1 schemas were loaded")

#@<> BUG#34599319 - cleanup
session.run_sql("DROP SCHEMA IF EXISTS !;", [ tested_schema ])

#@<> BUG#34604763 - new s3Region option
with write_profile(local_aws_config_file, "profile " + local_aws_profile, { "region": "invalid" }):
    with write_profile(local_aws_credentials_file, local_aws_profile, { "aws_access_key_id": aws_settings["aws_access_key_id"], "aws_secret_access_key": aws_settings["aws_secret_access_key"] }):
        EXPECT_SUCCESS({ "s3Region": aws_settings.get("region", default_aws_region), "s3Profile": local_aws_profile, "s3ConfigFile": local_aws_config_file, "s3CredentialsFile": local_aws_credentials_file })

#@<> cleanup
cleanup_tests(load_tests = True)
