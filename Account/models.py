from django.db import models
from django.contrib.auth.models import User

class Account(models.Model):
    user = models.OneToOneField(User, on_delete = models.CASCADE)
    birthday = models.DateField(null=True)
    gender = models.CharField(
        max_length = 6,
        choices = [('Male', 'Male'), ('Female','Female')]
    )
    mobile = models.CharField(max_length=15, unique=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    profile_image = models.ImageField(upload_to='account/', max_length=250, null=True, blank=True)
    face_data = models.BinaryField(null=True, blank=True)
    pin = models.CharField(max_length=4,null=True)

    def __str__(self):
        return self.user.username


class Transactions(models.Model):
    TRANSACTION_CHOICES = (
        ('withdraw','Withdraw'),
        ('deposit','Deposit'),
        ('load','Load')
    )
    user = models.ForeignKey(User,on_delete = models.CASCADE)
    amount = models.DecimalField(max_digits=10,decimal_places=2) 
    date = models.DateField(auto_now_add=True)
    transaction_type = models.CharField(max_length=10,choices=TRANSACTION_CHOICES) 
    sender = models.CharField(max_length=15, null=True)
    receiver = models.CharField(max_length=15, null=True)

   
