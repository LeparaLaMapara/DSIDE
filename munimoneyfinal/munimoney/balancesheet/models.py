from django.db import models

# Create your models here.
class BalSheet(models.Model):
	total_amount = models.DecimalField(max_digits=20,decimal_places=2)
	fin_year = models.DateTimeField()
	account_type = models.TextField()
	label = models.TextField()
	mun_name = models.TextField()
	mun_code = models.CharField(max_length=5)
	province = models.TextField()
	latitude = models.TextField()
	longitude = models.TextField()


	def __str__(self):
		return self.mun_name

class ProfileStats(models.Model):
	mun_code = models.CharField(max_length=5)
	efficient_measure = models.DecimalField(max_digits=12,decimal_places=5)
	wellfare_measure = models.DecimalField(max_digits=12,decimal_places=5)
	fin_date = models.DateTimeField()
	province = models.TextField()
	profile = models.IntegerField()

	def __str__(self):
		return self.profile
	


	
