# PoGo-Captcha

# Todo
- Implement the ability to save logs in a file & split accounts in different files to obtain three files: a file containing all the account that didn't had a captcha, a file with all the account that had a captcha and it has been solved, and a file containing all the accounts who had any sort of issue (login/captcha solving or anything else)
- Implement PGM config.ini reading to import accounts
- Implement reading location from accounts.csv, in this way every account can have a different location
- Implement threads, in this way we could speed up the tool

# Requirements
- pip install -r requirements.txt
- Don't forget Chromedriver & PhantomJS (follow Pikaptcha guide)

# How to use
```
  -h, --help            show this help message and exit
  -ac ACCOUNTCSV, --accountcsv ACCOUNTCSV
                        Load accounts from CSV file containing
                        "auth_service,username,password" lines
  -a AUTH_SERVICE, --auth_service AUTH_SERVICE
                        Auth Service ('ptc' or 'google')
  -hk HASH_KEY, --hash_key HASH_KEY
                        Bossland Hash Key
  -u USERNAME, --username USERNAME
                        Username
  -p PASSWORD, --password PASSWORD
                        Password
  -l LOCATION, --location LOCATION
                        Location
  -px PROXY, --proxy PROXY
                        Specify a socks5 proxy url
  -c CAPTCHAKEY, --captchakey CAPTCHAKEY
                        2Captcha Api Key
  -ch CHROMEDIR, --chromedir CHROMEDIR
                        Path to chrome binary
  -v, --verbose         Show debug messages
```

# Known issues
Someone is experiencing issues with selenium/phatomjs/chromedriver. Try with different versions of these.
Someone experienced issues running Python x86. Solved installing x64.

# Credits
Mainly based on Pikaptcha script for solving captcha. Improved adding new 'pageurl' parameter requested by 2captcha.
Thanks to Chrales & Fokse for ideas, tests and coding help.
