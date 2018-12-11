# -*- coding: utf-8 -*-
#from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def index(request):
	return render(request, "personal/home.html")

def services(request):
	return render(request, "personal/services.html", {"content": ["We provide services within the Data Science field","Data Explonatory Analysis"]})

