from django.urls import path
from django.views.generic import ListView, DetailView
from balancesheet.models import BalSheet

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('profile2012', views.profile2012, name='Profile2012'),
    path('profile2013', views.profile2013, name='Profile2013'),
    path('profile2014', views.profile2014, name='Profile2014'),
    path('profile2015', views.profile2015, name='Profile2015'),
    path('avarageProfile', views.avarageProfile, name='avarageProfile'),
    path('profiles', views.profiles, name='profiles'),
    path('document', views.document, name='document'),
    path('profileStatsData', views.profileStatsData, name='profileStatsData'),
    path('tree', views.tree, name='decisionTree'),
    path('search', views.search, name='search'),
    path('sunburst', views.sunburst, name='sunburst'),
    path('burst2012', views.burst2012, name='burst2012'),
    path('burst2013', views.burst2013, name='burst2013'),
    path('burst2014', views.burst2014, name='burst2014'),
    path('burst2015', views.burst2015, name='burst2015'),
    path('ExpenseSunburst', views.ExpenseSunburst, name='ExpenseSunburst'),
    path('Expburst2012', views.Expburst2012, name='Expburst2012'),
    path('Expburst2013', views.Expburst2013, name='Expburst2013'),
    path('Expburst2014', views.Expburst2014, name='Expburst2014'),
    path('Expburst2015', views.Expburst2015, name='Expburst2015'),
    path('SVMpage', views.SVMpage, name='SVMpage'),
    path('SVM', views.SVM, name='SVM'),
    path('classify', views.classify, name='classify'),
    path('RandomTree', views.RandomTree, name='RandomTree'),
    path('MunSearch', views.MunSearch, name='MunSearch'),
    path('Searching', views.Searching, name='Searching'),
]
