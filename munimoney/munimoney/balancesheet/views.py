# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http import HttpResponse
from django.shortcuts import render
import os
import json
import csv
import numpy as np
import psycopg2
import pickle
import math
import pandas as pd
from json import JSONEncoder
import numpy as np
import codecs
import collections


from sklearn import svm
from sklearn.ensemble import RandomForestRegressor
from sklearn import tree
from django.shortcuts import render_to_response
from django.views.decorators.csrf import ensure_csrf_cookie

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Create your views here.


def profile2012(request):
	json_data = os.path.join(BASE_DIR, 'balancesheet/static/json', "result2012.json")
	data = open(json_data).read()
	data2 = json.dumps(data) # json formatted string
	#rows = profileStatsData()
	rows = profileStatsData2012()
	#return render(request, 'balancesheet/test.html', {'data': data2,}, content_type='application/xhtml+xml')
	return render(request, 'balancesheet/profiles.html', {'data': data2,'row':rows})


def profile2013(request):
	json_data = os.path.join(BASE_DIR, 'balancesheet/static/json', "result2013.json")
	data = open(json_data).read()
	data2 = json.dumps(data) # json formatted string
	rows = profileStatsData2013()
	#return render(request, 'balancesheet/test.html', {'data': data2,}, content_type='application/xhtml+xml')
	return render(request, 'balancesheet/profiles.html', {'data': data2,'row':rows})



def profile2014(request):
	json_data = os.path.join(BASE_DIR, 'balancesheet/static/json', "result2014.json")
	data = open(json_data).read()
	data2 = json.dumps(data) # json formatted string
	rows = profileStatsData2014()
	#return render(request, 'balancesheet/test.html', {'data': data2,}, content_type='application/xhtml+xml')
	return render(request, 'balancesheet/profiles.html', {'data': data2,'row':rows})


def profile2015(request):
	json_data = os.path.join(BASE_DIR, 'balancesheet/static/json', "result2015.json")
	data = open(json_data).read()
	data2 = json.dumps(data) # json formatted string
	rows = profileStatsData2015()
	rowsPro = profileByPro()
	#return render(request, 'balancesheet/test.html', {'data': data2,}, content_type='application/xhtml+xml')
	return render(request, 'balancesheet/profiles.html', {'data': data2,'row':rows, 'row1':rowsPro, })


def avarageProfile(request):
	json_data = os.path.join(BASE_DIR, 'balancesheet/static/json', "resultAva.json")
	data = open(json_data).read()
	data2 = json.dumps(data) # json formatted string
	rows = profileStatsData()
	return render(request, 'balancesheet/profiles.html', {'data': data2,'row':rows})


def index(request):	
	return render(request, 'balancesheet/index.html', {})

def profiles(request):	
	return render(request, 'balancesheet/profiles.html', {})

def document(request):	
	return render(request, 'balancesheet/info.html', {})

def convert(data):
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(convert, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert, data))
    else:
        return data

def profileStatsData():
	""" query data from the vendors table """
	rows = []
	profile_array = {}
	conn = psycopg2.connect(database="munimoney", user="postgres", password="46926461@Lejaka", host="127.0.0.1", port="5432")
	#conn = None
	try:
		conn = psycopg2.connect(database="munimoney", user="postgres", password="46926461@Lejaka", host="127.0.0.1", port="5432")
		cur = conn.cursor()
        
        
		for i in range(1,5):
			cur.execute("SELECT mun_code, profile from profiles where profile=%i" %(i))
			rows = cur.fetchall()
			profile_num = len(rows)
			profile_array[i] = profile_num      
			#cur.close()

	except (Exception, psycopg2.DatabaseError) as error:
		print(error)

	finally:
		if conn is not None:
		    #conn.close()
			print("Connection closed")

	#print(profile_array)	
	rows = [profile_array]
	print(rows)
	#rows = dict(map(reversed, rows))

    #rows = [{'1':15, '2':54, '3':100, '4':7}]
    
	#rows = convert(rows)
	#print(rows)
	return rows

def profileStatsData2012():
	""" query data from the vendors table """
	rows12 = []
	profile_array = {}
	conn = psycopg2.connect(database="munimoney", user="postgres", password="46926461@Lejaka", host="127.0.0.1", port="5432")
	#conn = None
	try:
		conn = psycopg2.connect(database="munimoney", user="postgres", password="46926461@Lejaka", host="127.0.0.1", port="5432")
		cur = conn.cursor()
        
        
		for i in range(1,5):
			cur.execute("SELECT mun_code, profile from balancesheet_profilestats where fin_date='2012' AND profile=%i" %(i))
			rows = cur.fetchall()
			profile_num = len(rows)
			profile_array[i] = profile_num      
			#cur.close()

	except (Exception, psycopg2.DatabaseError) as error:
		print(error)

	finally:
		if conn is not None:
		    #conn.close()
			print("Connection closed")

	#print(profile_array)	
	rows12 = [profile_array]
	print(rows12)
	#rows = dict(map(reversed, rows))

    #rows = [{'1':15, '2':54, '3':100, '4':7}]
    
	#rows = convert(rows)
	#print(rows)
	return rows12
	
def profileStatsData2013():
	""" query data from the vendors table """
	rows13 = []
	profile_array = {}
	conn = psycopg2.connect(database="munimoney", user="postgres", password="46926461@Lejaka", host="127.0.0.1", port="5432")
	#conn = None
	try:
		conn = psycopg2.connect(database="munimoney", user="postgres", password="46926461@Lejaka", host="127.0.0.1", port="5432")
		cur = conn.cursor()
        
        
		for i in range(1,5):
			cur.execute("SELECT mun_code, profile from balancesheet_profilestats where fin_date='2013' AND profile=%i" %(i))
			rows = cur.fetchall()
			profile_num = len(rows)
			profile_array[i] = profile_num      
			#cur.close()

	except (Exception, psycopg2.DatabaseError) as error:
		print(error)

	finally:
		if conn is not None:
		    #conn.close()
			print("Connection closed")

	#print(profile_array)	
	rows13 = [profile_array]
	print(rows13)
	#rows = dict(map(reversed, rows))

    #rows = [{'1':15, '2':54, '3':100, '4':7}]
    
	#rows = convert(rows)
	#print(rows)
	return rows13
	
def profileStatsData2014():
	""" query data from the vendors table """
	rows14 = []
	profile_array = {}
	conn = psycopg2.connect(database="munimoney", user="postgres", password="46926461@Lejaka", host="127.0.0.1", port="5432")
	#conn = None
	try:
		conn = psycopg2.connect(database="munimoney", user="postgres", password="46926461@Lejaka", host="127.0.0.1", port="5432")
		cur = conn.cursor()
        
        
		for i in range(1,5):
			cur.execute("SELECT mun_code, profile from balancesheet_profilestats where fin_date='2014' AND profile=%i" %(i))
			rows = cur.fetchall()
			profile_num = len(rows)
			profile_array[i] = profile_num      
			#cur.close()

	except (Exception, psycopg2.DatabaseError) as error:
		print(error)

	finally:
		if conn is not None:
		    #conn.close()
			print("Connection closed")

	#print(profile_array)	
	rows14 = [profile_array]
	print(rows14)
	#rows = dict(map(reversed, rows))

    #rows = [{'1':15, '2':54, '3':100, '4':7}]
    
	#rows = convert(rows)
	#print(rows)
	return rows14
	
def profileStatsData2015():
	""" query data from the vendors table """
	rows15 = []
	profile_array = {}
	conn = psycopg2.connect(database="munimoney", user="postgres", password="46926461@Lejaka", host="127.0.0.1", port="5432")
	#conn = None
	try:
		conn = psycopg2.connect(database="munimoney", user="postgres", password="46926461@Lejaka", host="127.0.0.1", port="5432")
		cur = conn.cursor()
        
        
		for i in range(1,5):
			cur.execute("SELECT mun_code, profile from balancesheet_profilestats where fin_date='2015' AND profile=%i" %(i))
			rows = cur.fetchall()
			profile_num = len(rows)
			profile_array[i] = profile_num      
			#cur.close()

	except (Exception, psycopg2.DatabaseError) as error:
		print(error)

	finally:
		if conn is not None:
		    #conn.close()
			print("Connection closed")

	#print(profile_array)	
	rows15 = [profile_array]
	print(rows15)
	#rows = dict(map(reversed, rows))

    #rows = [{'1':15, '2':54, '3':100, '4':7}]
    
	#rows = convert(rows)
	#print(rows)
	return rows15
	
	
def profileByPro():
	""" query data from the vendors table """
	rowsPro = []
	conn = psycopg2.connect(database="munimoney", user="postgres", password="46926461@Lejaka", host="127.0.0.1", port="5432")
	cur = conn.cursor()
	#conn = None
	try:
		cur.execute("SELECT mun_code, profile, province from balancesheet_profilestats where fin_date='2015'")
		rowsPro = cur.fetchall()
		#convert unicode to string 
		rowsPro = convert(rowsPro)
	except (Exception, psycopg2.DatabaseError) as error:
		print(error)
	finally:
		if conn is not None:
		    #conn.close()
			print("Connection closed")
	print(rowsPro)
	return rowsPro
		
			
def profileStats(request):
    
    return render_to_response('balancesheet/Gauge.html', {})
	
def tree(request):
    
    return render_to_response('balancesheet/tree.html', {})
		
def searchMun():
	rowsSearch = []
	rowsSearchFin = []
	conn = psycopg2.connect(database="munimoney", user="postgres", password="46926461@Lejaka", host="127.0.0.1", port="5432")
	cur = conn.cursor()
	try:
		cur.execute("SELECT mun_code, profile, province, fin_date from balancesheet_profilestats where fin_date='2012' and mun_code='WC053'")
		rowsSearch = cur.fetchall()
		
		#convert unicode to string 
		rowsSearch = convert(rowsSearch)
		for x in rowsSearch:
			y = list(x)
			rowsSearchFin.append(y)
	except (Exception, psycopg2.DatabaseError) as error:
		print(error)
	finally:
		if conn is not None:
		    #conn.close()
			print("Connection closed")
	#print(rowsSearch)
	return rowsSearchFin
	
""" def search(request):
	rowsSearch = searchMun()
	print(rowsSearch)
	return render(request, 'balancesheet/search.html', {'mun_code':rowsSearch})
"""	
	
def search(request):
	rows = searchMun()
	print(rows)
	return render(request, 'balancesheet/search.html', {'row':rows})
	

	
def sunburstData(name):
	dataname = name + ".csv"		
	sun_data_list = []
	sun_data = os.path.join(BASE_DIR, 'balancesheet/static/sunburst', dataname)
	with open(sun_data, 'r') as csvfile:
		spamreader = csv.reader(csvfile)
		for row in spamreader:
			sun_data_list.append(row)
	data = ""
	total = 0 
	for row in sun_data_list:
		data += row[0] + "," + row[1] + "\n"
		#values[row[0]] = row[1]
		total += float(row[1])
	data = convert(data)
	print(data)
	return data, total


#IncProp Average 
def sunburst(request):
	profile1,total1 = sunburstData('IncProp_avg1')
	profile2,total2 = sunburstData('IncProp_avg2')
	profile3,total3 = sunburstData('IncProp_avg3') 
	return render(request, 'balancesheet/sunburst2.html', {'data': [profile1, total1, profile2, total2, profile3, total3]})

#ExpProp Average 
def ExpenseSunburst(request):
	profile1,total1 = sunburstData('ExpProp_avg1')
	profile2,total2 = sunburstData('ExpProp_avg2')
	profile3,total3 = sunburstData('ExpProp_avg3')
	return render(request, 'balancesheet/ExpSunburst.html', {'data': [profile1, total1, profile2, total2, profile3, total3]})


#IncomeProp by year
def burst2012(request):
	profile1,total1 = sunburstData('IncProp_Profile1_2012')
	profile2,total2 = sunburstData('IncProp_Profile2_2012')
	profile3,total3 = sunburstData('Inc_prop_profile3_2012')
	#return render(request, 'balancesheet/sunburst2.html', {'profile1': profile1, 'total1': total1, 'profile2': profile2, 'total2': total2})
	return render(request, 'balancesheet/sunburst2.html', {'data': [profile1, total1, profile2, total2, profile3, total3]})

def burst2013(request):
	profile1,total1 = sunburstData('IncProp_profile1_2013')
	profile2,total2 = sunburstData('IncProp_profile2_2013')
	profile3,total3 = sunburstData('Incempty')
	#return render(request, 'balancesheet/sunburst2.html', {'profile1': profile1, 'total1': total1, 'profile2': profile2, 'total2': total2})
	return render(request, 'balancesheet/sunburst2.html', {'data': [profile1, total1, profile2, total2, profile3, total3]})

def burst2014(request):
	profile1,total1 = sunburstData('IncProp_Profile1_2014')
	profile2,total2 = sunburstData('IncProp_profile2_2014')
	profile3,total3 = sunburstData('Incempty')
	#return render(request, 'balancesheet/sunburst2.html', {'profile1': profile1, 'total1': total1, 'profile2': profile2, 'total2': total2})
	return render(request, 'balancesheet/sunburst2.html', {'data': [profile1, total1, profile2, total2, profile3, total3]})

def burst2015(request):
	profile1,total1 = sunburstData('IncProp_profile1_2015')
	profile2,total2 = sunburstData('IncProp_profile2_2015')
	profile3,total3 = sunburstData('Incempty')
	#return render(request, 'balancesheet/sunburst2.html', {'profile1': profile1, 'total1': total1, 'profile2': profile2, 'total2': total2})
	return render(request, 'balancesheet/sunburst2.html', {'data': [profile1, total1, profile2, total2, profile3, total3]})



#Exp by year
def Expburst2012(request):
	profile1,total1 = sunburstData('ExpProp_profile1_2012')
	profile2,total2 = sunburstData('ExpProp_Profile2_2012')
	profile3,total3 = sunburstData('ExpProp_Profile3_2012')
	return render(request, 'balancesheet/ExpSunburst.html', {'data': [profile1, total1, profile2, total2, profile3, total3]})

def Expburst2013(request):
	profile1,total1 = sunburstData('ExpProp_Profile1_2013')
	profile2,total2 = sunburstData('ExpProp_Profile2_2013')
	profile3,total3 = sunburstData('Incempty')
	return render(request, 'balancesheet/ExpSunburst.html', {'data': [profile1, total1, profile2, total2, profile3, total3]})

def Expburst2014(request):
	profile1,total1 = sunburstData('ExpProp_Profile1_2014')
	profile2,total2 = sunburstData('ExpProp_Profile2_2014')
	profile3,total3 = sunburstData('Incempty')
	return render(request, 'balancesheet/ExpSunburst.html', {'data': [profile1, total1, profile2, total2, profile3, total3]})

def Expburst2015(request):
	profile1,total1 = sunburstData('ExpProp_Profile1_2015')
	profile2,total2 = sunburstData('ExpProp_Profile2_2015')
	profile3,total3 = sunburstData('Incempty')
	return render(request, 'balancesheet/ExpSunburst.html', {'data': [profile1, total1, profile2, total2, profile3, total3]})


from django.views.decorators.csrf import ensure_csrf_cookie
#recieve input and claculate prediction

def SVM(request):
	
	print(request.POST)  #returns a dictionary

	#STEP1: Input is immutable  therefore need to follow this method..
	if("EmpAdultProp" in request.POST and "IncomePovertyProp" in request.POST
	 and "OvercrowdedProp" in request.POST and "MatricProp" in request.POST
	 and "LessGrade9Prop" in request.POST and "NonPoor" in request.POST
	 and "YesProp" in request.POST and "repairsPPE" in request.POST
	 and "OppSurplusMargin" in request.POST and "Current Ratio" in request.POST):
	 	
		 the_data = request.POST
		 EmpAdult_Prop = the_data["EmpAdultProp"]
		 IncPoverty_Prop = the_data["IncomePovertyProp"]
		 Overcrowded_Prop = the_data["OvercrowdedProp"] 
		 Matric_Prop = the_data["MatricProp"] 
		 LessGrade9 = the_data["LessGrade9Prop"]
		 NonPoor = the_data["NonPoor"]
		 Citizenship = the_data["YesProp"]
		 repairs_PPE = the_data["repairsPPE"]
		 OppSurplusMargin = the_data["OppSurplusMargin"]
		 CurrentRatio = the_data["Current Ratio"]
	
	
	#STEP2: empty dataframe
	user_input = pd.DataFrame()	
	curr_val = [{"At least one employed adult": EmpAdult_Prop, "Income-poor": IncPoverty_Prop, "Overcrowded": Overcrowded_Prop,
	"Matric/matric equivalent": Matric_Prop,  "Less than Grade9": LessGrade9, "Non-poor": NonPoor, "Yes_y": Citizenship,
	   "repairs_PPE":repairs_PPE, "OppSurplusMargin": OppSurplusMargin,  "currRatio":  CurrentRatio}]
	curr_val = pd.DataFrame(curr_val)
	curr_val = curr_val[["At least one employed adult", "Income-poor", "Overcrowded", "Matric/matric equivalent", "Less than Grade9", "Non-poor", "Yes_y",
	'repairs_PPE', "OppSurplusMargin", 'currRatio']]


	#STEP3: load trained model
	filename = '/home/dside/djangotutorials/munimoney/balancesheet/static/SVM/finalized_model.sav'
	loaded_model = pickle.load(open(filename, 'rb'))
	result = loaded_model.predict(curr_val)
	result = result.tolist()

	return HttpResponse(json.dumps(result), content_type = 'application/json')




#load page
@ensure_csrf_cookie
def SVMpage(request):
	return render(request, 'balancesheet/SVM.html')	
	
	

#THABANG PREDICTION MODEL
def RandomTree(request):


	req = convert(request.POST)  #returns a dictionary
	print(req)

	#STEP1: Input is immutable  therefore need to follow this method..
	if("Aleast_employedadult" in request.POST and "NO_employedadult" in request.POST
	 and "doing_nothing" in request.POST and "Multi_poor" in request.POST
	 and "Neither_parents" in request.POST and "matric" in request.POST):
		the_data = req	
		Aleast_employedadult  = 	float(the_data["Aleast_employedadult"])/100.0
		NO_employedadult  = float(the_data["NO_employedadult"])/100.0
		doing_nothing  = float(the_data["doing_nothing"])/100.0
		Multi_poor = float(the_data["Multi_poor"])/100.0
		Neither_parents  = float(the_data["Neither_parents"])/100.0
		matric = float(the_data["matric"])/100.0
	
		print(matric)
	#STEP2: empty dataframe
	curr_val = [{"Aleast_employedadult": Aleast_employedadult, "NO_employedadult": NO_employedadult, "doing_nothing": doing_nothing,
	 "Multi_poor": Multi_poor, "Neither_parents": Neither_parents, "matric": matric }]
	curr_val = pd.DataFrame(curr_val)
	curr_val = curr_val[['Aleast_employedadult', 'NO_employedadult', 'doing_nothing','Multi_poor','Neither_parents','matric']]


	#STEP3: load trained model
	loaded_model = pickle.load(
	open(str('/home/dside/djangotutorials/munimoney/balancesheet/static/Model/forest.pkl'),'rb'))
	result = loaded_model.predict(curr_val)
	
	result = result.tolist()
	result = json.dumps(result)
	print(result)


	return HttpResponse(result, content_type = 'application/json')

@ensure_csrf_cookie
def classify(request):
	return render(request,'balancesheet/prediction.html', {})


	
