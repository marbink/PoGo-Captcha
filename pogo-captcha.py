import time
import string
from pgoapi import PGoApi
from pgoapi.utilities import f2i
from pgoapi import utilities as util
from pgoapi.exceptions import AuthException, ServerSideRequestThrottlingException, NotLoggedInException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import urllib2

#Edit these!
csv_file = "accounts.csv"
captchakey2 = ""
loc = "43.717497, 10.402206" #location


def openurl(address):
    try:
        urlresponse = urllib2.urlopen(address).read()
        return urlresponse        
    except urllib2.HTTPError, e:
        print("HTTPError = " + str(e.code))
    except urllib2.URLError, e:
        print("URLError = " + str(e.code))
    except Exception:
        import traceback
        print("Generic Exception: " + traceback.format_exc())
    print("Request to " + address + "failed.")    
    return "Failed"


def activateUser(api, captchatoken):
    #print ("Recaptcha token: {}".format(captchatoken))
    req = api.create_request()
    req.verify_challenge(token = captchatoken)
    response = (":".join("{:02x}".format(ord(c)) for c in captchatoken))
    response = req.call()
    print(response)


def solveCaptchas(mode, username, password, location, captchakey2):
    print(mode)
    print(username)
    print(password + "|")
    captchatimeout=3
    login_retry = 0
    
    user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) " + "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.57 Safari/537.36")
    api = PGoApi()
    location = location.replace(" ", "")
    location = location.split(",")
    api.set_position(float(location[0]), float(location[1]), 0.0)
    while (login_retry < 3):
        print("Login...")
        if api.login(mode, username, password):
            break
        login_retry = login_retry + 1
    if(login_retry == 3):
        print(("Login failed for {user}. Check data and try again.").format(user = username))
        return
    time.sleep(10)
    req = api.create_request()
    req.check_challenge()
    response = req.call()
    
    captcha_url = response['responses']['CHECK_CHALLENGE']['challenge_url'];
    
    
    if len(captcha_url) == 1:
        print(("No captcha for user: {user}").format(user = username))
        #skip, captcha not necessary
    else:
        print(("Captcha required for user: {user}").format(user = username))
	#print("CaptchaURL: {}".format(captcha_url))
        if captchakey2 != "":
            dcap = dict(DesiredCapabilities.PHANTOMJS)
            dcap["phantomjs.page.settings.userAgent"] = user_agent
            driver = webdriver.PhantomJS(desired_capabilities=dcap)
        else:
            driver = webdriver.Chrome()
            driver.set_window_size(600, 600)
            
        driver.get(captcha_url)
        
        if captchakey2 == "":
            #Do manual captcha entry
            print("You did not pass a 2captcha key. Please solve the captcha manually.")
            elem = driver.find_element_by_class_name("g-recaptcha")
            driver.execute_script("arguments[0].scrollIntoView(true);", elem)
            # Waits 1 minute for you to input captcha
            try:
                WebDriverWait(driver, 60).until(EC.text_to_be_present_in_element_value((By.NAME, "g-recaptcha-response"), ""))
                print "Solved captcha"
                token = driver.execute_script("return grecaptcha.getResponse()")
                #print ("Recaptcha token: {}".format(token))
                activateUser(api, token)
                time.sleep(1)
            except TimeoutException, err:
                print("Timed out while manually solving captcha")
        else:
            # Now to automatically handle captcha
            print("Starting autosolve recaptcha")
            html_source = driver.page_source
            gkey_index = html_source.find("https://www.google.com/recaptcha/api2/anchor?k=") + 47
            gkey = html_source[gkey_index:gkey_index+40]
            recaptcharesponse = "Failed"
            while(recaptcharesponse == "Failed"):
                recaptcharesponse = openurl("http://2captcha.com/in.php?key=" + captchakey2 + "&method=userrecaptcha&googlekey=" + gkey + "&pageurl=" + captcha_url)
            captchaid = recaptcharesponse[3:]
            recaptcharesponse = "CAPCHA_NOT_READY"
            elem = driver.find_element_by_class_name("g-recaptcha")
            print"We will wait 10 seconds for captcha to be solved by 2captcha"
            start_time = time.clock()
            timedout = False
            while recaptcharesponse == "CAPCHA_NOT_READY":
                time.sleep(10)            
                elapsedtime = time.clock() - start_time
                if elapsedtime > captchatimeout:
                    print("Captcha timeout reached. Exiting.")
                    timedout = True
                    break
                print "Captcha still not solved, waiting another 10 seconds."
                recaptcharesponse = "Failed"
                while(recaptcharesponse == "Failed"):
                    recaptcharesponse = openurl("http://2captcha.com/res.php?key=" + captchakey2 + "&action=get&id=" + captchaid)
            if timedout == False:       
                solvedcaptcha = recaptcharesponse[3:]
                captchalen = len(solvedcaptcha)
                elem = driver.find_element_by_name("g-recaptcha-response")
                elem = driver.execute_script("arguments[0].style.display = 'block'; return arguments[0];", elem)
                elem.send_keys(solvedcaptcha)      
                print "Solved captcha"                          
            token = driver.execute_script("return grecaptcha.getResponse()")
            
            
            activateUser(api, token)
    
with open(csv_file, 'r') as f:
    for num, line in enumerate(f, 1):
        if len(line) == 0 or line.startswith('#'):
            continue
        num_fields = line.count(',') + 1
        fields = line.split(",")
        if num_fields == 3:
            solveCaptchas(fields[0], fields[1], fields[2].replace('\n', '').replace('\r', ''), loc, captchakey2)
        if num_fields == 2:
            solveCaptchas("ptc", fields[0], fields[1].replace('\n', '').replace('\r', ''), loc, captchakey2)

time.sleep(10)

	
