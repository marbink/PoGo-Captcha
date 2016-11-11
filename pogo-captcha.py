import time
import string
import argparse
from pgoapi import PGoApi
from pgoapi.exceptions import AuthException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import urllib2
import sys
import os
import platform

config = None

def init_config():
    parser = argparse.ArgumentParser()

    # Read passed in Arguments
    parser.add_argument('-ac', '--accountcsv',
                        help='Load accounts from CSV file containing "auth_service,username,passwd" lines')
    parser.add_argument("-a", "--auth_service", help="Auth Service ('ptc' or 'google')")
    parser.add_argument("-u", "--username", help="Username")
    parser.add_argument("-p", "--password", help="Password")
    parser.add_argument("-l", "--location", help="Location", required=True)
    parser.add_argument("-px", "--proxy", help="Specify a socks5 proxy url", default=False)
    parser.add_argument("-c", "--captchakey", help="2Captcha Api Key", default="")
    parser.add_argument("-v", "--verbose", help="Show debug messages", action='store_true')
    config = parser.parse_args()

    # Checking arguments
    if not config.accountcsv:
        if not (config.username and config.password and config.auth_service):
            parser.error("-ac/--accountcsv parameter or -u/--username + -p/--password + -a/--auth_service CANNOT be empty")
        else:
            if config.auth_service not in ['ptc', 'google']:
                parser.error("Invalid auth service specified! ('ptc' or 'google')")

    return config


# Print functions
def print_debug(string, username = None):
    if not(config and config.verbose):
        return
    if username:
        print("[DEBUG][{user}] {data}".format(user = username, data = string))
    else:
        print("[DEBUG] {data}".format(data = string))

def print_info(string, username = None):
    if username:
        print("[ INFO][{user}] {data}".format(user = username, data = string))
    else:
        print("[ INFO] {data}".format(data = string))
        
def print_error(string, username = None):
    if username:
        print("[ERROR][{user}] {data}".format(user = username, data = string))
    else:
        print("[ERROR] {data}".format(data = string))

              
def openurl(address):
    try:
        urlresponse = urllib2.urlopen(address).read()
        return urlresponse        
    except urllib2.HTTPError, e:
        print_debug("HTTPError = " + str(e.code))
    except urllib2.URLError, e:
        print_debug("URLError = " + str(e.code))
    except Exception:
        import traceback
        print_debug("Generic Exception: " + traceback.format_exc())
    print_error("Request to " + address + "failed.")    
    return "Failed"

def get_encryption_lib_path():

    # win32 doesn't mean necessarily 32 bits
    if sys.platform == "win32" or sys.platform == "cygwin":
        if platform.architecture()[0] == '64bit':
            lib_name = "encrypt64.dll"
        else:
            lib_name = "encrypt32.dll"

    elif sys.platform == "darwin":
        lib_name = "libencrypt-osx-64.so"

    elif os.uname()[4].startswith("arm") and platform.architecture()[0] == '32bit':
        lib_name = "libencrypt-linux-arm-32.so"

    elif os.uname()[4].startswith("aarch64") and platform.architecture()[0] == '64bit':
        lib_name = "libencrypt-linux-arm-64.so"

    elif sys.platform.startswith('linux'):
        if "centos" in platform.platform():
            if platform.architecture()[0] == '64bit':
                lib_name = "libencrypt-centos-x86-64.so"
            else:
                lib_name = "libencrypt-linux-x86-32.so"
        else:
            if platform.architecture()[0] == '64bit':
                lib_name = "libencrypt-linux-x86-64.so"
            else:
                lib_name = "libencrypt-linux-x86-32.so"

    elif sys.platform.startswith('freebsd'):
        lib_name = "libencrypt-freebsd-64.so"

    else:
        err = "Unexpected/unsupported platform '{}'. If you have encrypt lib compiled for your platform, specify its location with '--encrypt-lib' parameter".format(sys.platform)
        print_error(err)
        raise Exception(err)

    lib_path = os.path.join(os.path.dirname(__file__), "pokecrypt-pgoapi", lib_name)

    if not os.path.isfile(lib_path):
        err = "Could not find {} encryption library {}".format(sys.platform, lib_path)
        print_error(err)
        raise Exception(err)

    return lib_path


def activateUser(api, captchatoken, username):
    print_debug("Recaptcha token: {}".format(captchatoken), username)
    response = api.verify_challenge(token = captchatoken)
    print_debug("Response:{}".format(response), username)


def solveCaptchas(mode, username, password, location, captchakey2):
    try:
        captchatimeout=1000
        max_login_retries = 5
        user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) " + "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.57 Safari/537.36")
        
        location = location.replace(" ", "")
        location = location.split(",")

        api = PGoApi()
        if config.proxy:
            api.set_proxy({'http': config.proxy, 'https': config.proxy}) #Need this? Proxy is not setted with set_authentication?
        api.activate_signature(get_encryption_lib_path())    
        api.set_position(float(location[0]), float(location[1]), 0.0)

        # Try to login (a few times, but don't get stuck here)
        i = 0
        while i < max_login_retries:
            try:
                if config.proxy:
                    api.set_authentication(provider=mode, username=username, password=password, proxy_config={'http': config.proxy, 'https': config.proxy})
                else:
                    api.set_authentication(provider=mode, username=username, password=password)
                break
            except AuthException:
                if i >= max_login_retries:
                    print_info('Exceeded login attempts. Skipping to next account.', username)
                    return
                else:
                    i += 1
                    print_error('Failed to login. Trying again in 10 seconds. Check the account if this error persist.', username)
                    time.sleep(10)

        print_info("Login OK [{num} attempt(s)]".format(num = (i + 1)), username)
                
        time.sleep(1)
        response = api.check_challenge()
        
        captcha_url = None

        try:
            captcha_url = response['responses']['CHECK_CHALLENGE']['challenge_url'];
        except Exception:
            print_info('Something wrong happened getting captcha. Check account. Skipping...', username)
            return
        
        if len(captcha_url) == 1:
            print_info("No captcha required", username)
            #skip, captcha not necessary
        else:
            print_info("Captcha required", username)
            print_debug("CaptchaURL: {}".format(captcha_url), username)
            
            if captchakey2 != "":
                dcap = dict(DesiredCapabilities.PHANTOMJS)
                dcap["phantomjs.page.settings.userAgent"] = user_agent
                driver = webdriver.PhantomJS(desired_capabilities=dcap)
            else:
                print_info("You did not pass a 2captcha key. Please solve the captcha manually.", username)
                try:
                    driver = webdriver.Chrome()
                    driver.set_window_size(600, 600)
                except Exception:
                    print_error("Chromedriver seems to have some problem. Do you have the latest version?")
                    return
                
            driver.get(captcha_url)
            
            if captchakey2 == "":
                #Do manual captcha entry
                
                elem = driver.find_element_by_class_name("g-recaptcha")
                driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                # Waits 1 minute for you to input captcha
                try:
                    WebDriverWait(driver, 60).until(EC.text_to_be_present_in_element_value((By.NAME, "g-recaptcha-response"), ""))
                    print_info("Solved captcha", username)
                    token = driver.execute_script("return grecaptcha.getResponse()")
                    driver.close()
                    print_debug("Recaptcha token: {}".format(token))
                    activateUser(api, token, username)
                    time.sleep(1)
                except TimeoutException, err:
                    print_info("Timed out while manually solving captcha", username)
            else:
                # Now to automatically handle captcha
                print_info("Starting autosolve recaptcha", username)
                html_source = driver.page_source
                gkey_index = html_source.find("https://www.google.com/recaptcha/api2/anchor?k=") + 47
                gkey = html_source[gkey_index:gkey_index+40]
                recaptcharesponse = "Failed"
                while(recaptcharesponse == "Failed"):
                    recaptcharesponse = openurl("http://2captcha.com/in.php?key=" + captchakey2 + "&method=userrecaptcha&googlekey=" + gkey + "&pageurl=" + captcha_url)
                captchaid = recaptcharesponse[3:]
                recaptcharesponse = "CAPCHA_NOT_READY"
                elem = driver.find_element_by_class_name("g-recaptcha")
                print_info("We will wait 10 seconds for captcha to be solved by 2captcha", username)
                start_time = time.clock()
                timedout = False
                while recaptcharesponse == "CAPCHA_NOT_READY":
                    time.sleep(10)            
                    elapsedtime = time.clock() - start_time
                    if elapsedtime > captchatimeout:
                        print_info("Captcha timeout reached. Exiting.", username)
                        timedout = True
                        break
                    print_info("Captcha still not solved, waiting another 10 seconds.", username)
                    recaptcharesponse = "Failed"
                    while(recaptcharesponse == "Failed"):
                        recaptcharesponse = openurl("http://2captcha.com/res.php?key=" + captchakey2 + "&action=get&id=" + captchaid)
                if timedout == False:       
                    solvedcaptcha = recaptcharesponse[3:]
                    captchalen = len(solvedcaptcha)
                    elem = driver.find_element_by_name("g-recaptcha-response")
                    elem = driver.execute_script("arguments[0].style.display = 'block'; return arguments[0];", elem)
                    elem.send_keys(solvedcaptcha)      
                    print_info("Solved captcha", username)
                token = driver.execute_script("return grecaptcha.getResponse()")
                
                
                activateUser(api, token, username)
    except Exception, e:
        print_error(repr(e), username)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print_debug(exc_type, username)
        print_debug(exc_tb.tb_lineno, username)

config = init_config()
if not config:
    exit()

if not config.accountcsv:
    try:
        solveCaptchas(config.auth_service, config.username, config.password, config.location, config.captchakey)
    except Exception, e:
        print_error("Unhandled exception.")
        print_debug(repr(e), username)
else:    
    with open(config.accountcsv, 'r') as f:
        for num, line in enumerate(f, 1):
            if len(line) == 0 or line.startswith('#'):
                continue
            num_fields = line.count(',') + 1
            fields = line.split(",")
            username = ""

            try:                
                if num_fields == 3:
                    username = fields[1]
                    solveCaptchas(fields[0], fields[1], fields[2].replace('\n', '').replace('\r', ''), config.location, config.captchakey)
                if num_fields == 2:
                    username = fields[0]
                    solveCaptchas("ptc", fields[0], fields[1].replace('\n', '').replace('\r', ''), config.location, config.captchakey)
            except Exception, e:
                print_error("Unhandled exception. Skipping to next account.")
                print_debug(repr(e), username)
            



	
