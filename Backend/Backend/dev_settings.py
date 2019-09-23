from .common_settings import *

DEBUG = True

DATABASES['default'].update({
    'NAME': 'ebay_django',
    'USER': 'root',
    'PASSWORD': 'root',
    'HOST': 'localhost',
    'PORT': '3306'
})