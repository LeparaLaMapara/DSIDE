from django.conf.urls import url, include
from django.views.generic import ListView, DetailView
from balancesheet.models import BalSheet

from django.conf.urls import url

from . import views

#urlpatterns = [url(r'^$', ListView.as_view(queryset=BalSheet.objects.all().order_by("fin_year")[:25],
#					template_name="balancesheet/test.html")),
#					url(r'^(?P<pk>\d+)$', DetailView.as_view(model= BalSheet,
#						template_name = 'balancesheet/post.html'))]

urlpatterns = [
    # ex: /polls/
    #url(r'^$', views.frontPage, name='frontPage'),
	url(r'^$', views.index, name='index'),
	url(r'^profile2012', views.profile2012, name='Profile2012'),
	url(r'^profile2013', views.profile2013, name='Profile2013'),
	url(r'^profile2014', views.profile2014, name='Profile2014'),
	url(r'^profile2015', views.profile2015, name='Profile2015'),
	url(r'^avarageProfile', views.avarageProfile, name='avarageProfile'),
	url(r'^profiles', views.profiles, name='profiles'),
	url(r'^document', views.document, name='document'),
	url(r'^profileStats', views.profileStats, name='profileStats'),
	url(r'^tree', views.tree, name='decisionTree'),
	url(r'^search', views.search, name='search'),
	url(r'^sunburst', views.sunburst, name='sunburst'),
	url(r'^burst2012', views.burst2012, name='burst2012'),	
	url(r'^burst2013', views.burst2013, name='burst2013'),
	url(r'^burst2014', views.burst2014, name='burst2014'),
	url(r'^burst2015', views.burst2015, name='burst2015'),
	url(r'^ExpenseSunburst', views.ExpenseSunburst, name='ExpenseSunburst'),
	url(r'^Expburst2012', views.Expburst2012, name='Expburst2012'),	
	url(r'^Expburst2013', views.Expburst2013, name='Expburst2013'),
	url(r'^Expburst2014', views.Expburst2014, name='Expburst2014'),	
	url(r'^Expburst2015', views.Expburst2015, name='Expburst2015'),	
	url(r'^SVMpage', views.SVMpage, name='SVMpage'),
	url(r'^SVM', views.SVM, name='SVM'),
	
	url(r'^classify', views.classify, name='classify'),
	url(r'^RandomTree', views.RandomTree, name='RandomTree'),
	

    
]
