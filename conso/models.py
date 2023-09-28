import random
from django.db import models
from django.contrib.auth.models import User

class Entreprise(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    nom_societe = models.CharField(default ="Nom de la societe", max_length=100, null=True, blank=True, verbose_name="Nom de l'entreprise ou de la société")
    telephone = models.CharField(default ="00000000", max_length=20,null=True, blank=True,verbose_name="Numéro de téléphone")
    domaine_act = models.CharField(default ="Domaine d'activité", max_length=100, null=True, blank=True, verbose_name="Domaine d'activité")
    localite = models.CharField(default ="Localite de la societe", max_length=100, null=True, blank=True, verbose_name="Localisation")
    
    
class Section(models.Model):
    entreprise = models.ForeignKey(Entreprise, null=True, blank=True, on_delete=models.CASCADE)
    nom_section = models.CharField(max_length=100, null=True, blank=True, verbose_name="Nom de la section")
    description = models.TextField(null=True, blank=True, verbose_name="Description")
    def __str__(self):
        return self.nom_section
    
class Variable(models.Model):
    libelle = models.CharField(max_length=100, null=True, blank=True, verbose_name="Nom de la variable")
    unite_mesure = models.CharField(max_length=100, null=True, blank=True,verbose_name="Unité de mesure de la variable")
    def __str__(self):
        return self.libelle
    


class Dispositif(models.Model):
    variable = models.ForeignKey(Variable, null=True, blank=True, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.CASCADE)
    numero_serie = models.CharField(max_length=100, null=True, blank=True, verbose_name="Numéro serie")
    nom_lieu = models.CharField(max_length=100,null=True,blank=True,verbose_name="Le lieu où se trouve le dispositif")    
    source_eau = models.CharField(max_length=100,null = True, blank=True, verbose_name="Source d'eau")
    latitude=models.FloatField(null=True,blank=True)
    longitude=models.FloatField(null=True,blank=True)
    altitude=models.FloatField(null=True,blank=True)
    precision=models.FloatField(null=True,blank=True)
    def __str__(self):
        return self.nom_lieu
    
class Consommation(models.Model):
    dispositif = models.ForeignKey(Dispositif, null=True, blank=True, on_delete=models.CASCADE)
    quantite = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)

class Budget(models.Model):
    entreprise = models.ForeignKey(Entreprise, null=True, blank=True, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    solde = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Ajoutez ce champ
    description = models.TextField(blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)


class Depense(models.Model):
    entreprise = models.ForeignKey(Entreprise, null=True, blank=True, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    budget = models.ForeignKey(Budget, null=True, blank=True, on_delete=models.SET_NULL)  # Référence au budget
    description = models.TextField(blank=True, null=True)  # Ajoutez un champ de description si nécessaire
    date_creation = models.DateTimeField(auto_now_add=True)


class Alert(models.Model):
    intitule = models.TextField()
    message = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)   