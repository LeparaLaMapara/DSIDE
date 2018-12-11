# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
import os

# Create your views here.
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def frontPage(request):
	json_data = os.path.join(BASE_DIR, 'balancesheet/static', "result2012.json")
	
	data = open(json_data).read()
	data2 = json.dumps(data) # json formatted string


	#return render(request, 'balancesheet/test.html', {'data': data2,}, content_type='application/xhtml+xml')
	return render(request, 'balancesheet/test.html', {'data': data2,})

