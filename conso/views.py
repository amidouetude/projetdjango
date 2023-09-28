from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
import numpy as np
from scipy import stats
from conso.models import Alert, Budget, Depense, Section, Dispositif, Entreprise, Consommation
from conso.serializers import ConsommationSerializer
from .forms import SectionForm, DispositifForm, EntrepriseForm, UserProfileForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from rest_framework.viewsets import ModelViewSet
from . import forms
import pandas as pd
import openpyxl
import statsmodels.api as sm
from django.contrib import messages



##### Accès vers la page d'acceuil
#Code pour le calcul de la consommation totale

#Affichage de la conso dans l'index
def index(request):
    try:
        if request.user.is_authenticated:
            user_id = request.user.id
            user_entreprise_id = get_object_or_404(Entreprise, user_id=user_id)
            sections = Section.objects.filter(entreprise_id=user_entreprise_id)
            today = date.today()
            start_date = today - timedelta(days=7)
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = datetime.combine(today, datetime.max.time())
            month_start = today.replace(day=1)
            next_month = month_start.replace(month=month_start.month % 12 + 1, year=month_start.year + month_start.month // 12)
            month_end = next_month - timedelta(days=1)
            thisday = date.today()
            start_of_week = thisday - timedelta(days=thisday.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            data = []  

            # Créez une liste des noms des jours de la semaine pour les six derniers jours
            # Créez une liste de noms de jours pour les 7 derniers jours
            dayli = datetime.today()
            last_seven_days = [dayli - timedelta(days=i) for i in range(6, -1, -1)]
            days_of_week = [day.strftime("%A") for day in last_seven_days]
            
            #determination de la consommation du jour
            daily_consommation = (Consommation.objects
                                .filter(dispositif__section__entreprise=user_entreprise_id,created_at__range=(start_of_day, end_of_day))
                                .aggregate(Sum('quantite'))['quantite__sum'])
            if daily_consommation is None:
                daily_consommation = 0 
            
            #determination de la consommation du jour
            weekly_consommation = (Consommation.objects
                                .filter(dispositif__section__entreprise=user_entreprise_id,created_at__range=(start_of_week, end_of_week))
                                .aggregate(Sum('quantite'))['quantite__sum'])
            if weekly_consommation is None:
                weekly_consommation = 0 
            
            daily_consommation_section = []
            weekly_consommation_section = []
            monthly_consommation_section = []
            
            for section in sections:
                monthly_consommation_section.append(Consommation.objects.filter(dispositif__section=section, created_at__range=(month_start, month_end)).aggregate(Sum('quantite'))['quantite__sum'])
                weekly_consommation_section.append(Consommation.objects.filter(dispositif__section=section, created_at__range=(start_of_week, end_of_week)).aggregate(Sum('quantite'))['quantite__sum'])
                daily_consommation_section.append(Consommation.objects.filter(dispositif__section=section, created_at__range=(start_of_day, end_of_day)).aggregate(Sum('quantite'))['quantite__sum'])
                    
            #Determination de la consommation du mois
            monthly_consommation = (Consommation.objects
                                .filter(dispositif__section__entreprise=user_entreprise_id,
                                created_at__range=(month_start, month_end))
                                .aggregate(Sum('quantite'))['quantite__sum'])
            if monthly_consommation is None:
                monthly_consommation = 0
            #determination de la consommation des 07 derniers jours
            data = (
                        Consommation.objects
                        .filter(dispositif__section__entreprise=user_entreprise_id,created_at__range=(start_date, today))
                        .values('created_at__date')
                        .annotate(quantite_sum=Sum('quantite'))
                    )
            #Consommation mensuelle
            twelve_months_ago = today - timedelta(days=365)
            monthly_data = (
                        Consommation.objects
                        .filter(dispositif__section__entreprise=user_entreprise_id,created_at__range=(twelve_months_ago, today))
                        .values('created_at__date')
                        .annotate(quantite_sum=Sum('quantite'))
                    )
        data_list = [{'day': item['created_at__date'], 'quantite_sum': item['quantite_sum']} for item in data]
        context = {
            'data': data_list,
            "sections": sections,
            "today": today,
            "days_of_week":days_of_week,
            "daily_consommation": daily_consommation,
            "weekly_consommation": weekly_consommation,
            "monthly_consommation": monthly_consommation,
            "daily_consommation_section": daily_consommation_section,
            "weekly_consommation_section": weekly_consommation_section,
            "monthly_consommation_section": monthly_consommation_section,
        }   
        
        return render(request, 'conso/index.html', context)
    except Exception as e:
        # Gérez l'exception ici, par exemple, affichez un message d'erreur ou redirigez l'utilisateur vers une page d'erreur.
        error_message = f"Une exception s'est produite : {e}"
        return render(request, 'conso/error.html', {'error_message': error_message})

##### Accès vers la vue des sections

#Accès vers la liste des sections
@login_required
def section(request):
    try:
        user_id = request.user.id
        user_entreprise_id = get_object_or_404(Entreprise, user_id=user_id)
        sections = Section.objects.filter(entreprise_id=user_entreprise_id)
        consom = []
        #determination du jour
        today = date.today()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        #Determination de la semaine
        thisday = datetime.today()
        start_of_week = thisday - timedelta(days=thisday.weekday())
        end_of_week = start_of_week + timedelta(days=6)
    #    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for section in sections:
            #Consommation générale par section
            total_consommation = Consommation.objects.filter(dispositif__section=section).aggregate(Sum('quantite'))['quantite__sum']
            if total_consommation is None:
                total_consommation = 0
            #Consommation par jour
            daily_consommation = Consommation.objects.filter(dispositif__section=section,created_at__range=(start_of_day, end_of_day)).aggregate(Sum('quantite'))['quantite__sum']
            if daily_consommation is None:
                daily_consommation = 0
            weekly_consommation = Consommation.objects.filter(dispositif__section=section,
                created_at__date__range=[start_of_week, end_of_week]
            ).values('created_at__date').aggregate(Sum('quantite'))['quantite__sum']
            if weekly_consommation is None:
                weekly_consommation = 0        
            month_start = today.replace(day=1)
            next_month = month_start.replace(month=month_start.month % 12 + 1, year=month_start.year + month_start.month // 12)
            month_end = next_month - timedelta(days=1)
            monthly_consommation = Consommation.objects.filter(dispositif__section=section, created_at__range=(month_start, month_end)).aggregate(Sum('quantite'))['quantite__sum']
            if monthly_consommation is None:
                monthly_consommation = 0
            consom.append({
                'section': section,
                'total_consommation': total_consommation,
                'daily_consommation': daily_consommation,
                'weekly_consommation': weekly_consommation,
                'monthly_consommation': monthly_consommation
            })
        ahmed={'consom':consom}
        return render(request,'conso/section/sections.html',ahmed)
    except Exception as e:
        # Gérer l'exception, par exemple, rediriger vers une page d'erreur
        return render(request, 'conso/error.html', {'error_message': str(e)})

#Creer une nouvelle section
@login_required
def add_section(request):
    try:
        if request.method == "POST":
            form=SectionForm(request.POST)
            if form.is_valid():
                section = form.save(commit = False)
                section.entreprise = Entreprise.objects.get(user_id=request.user.id)
                section.save()
                return redirect('section')
            else:
                return render(request,'conso/section/add_section.html',{'form':form})
        else:
            form = SectionForm()
        return render(request,'conso/section/add_section.html',{'form':form})
    except Exception as e:
        # Gérer l'exception, par exemple, rediriger vers une page d'erreur
        return render(request, 'conso/error.html', {'error_message': str(e)})

#Modifier une section existante
@login_required
def update_section(request, pk):
    try:
        section = Section.objects.get(id=pk)
        form=SectionForm(instance=section)
        if request.method=="POST":
            form = SectionForm(request.POST,instance=section)
            if form.is_valid():
                form.save()
                return redirect('section')
            else:
                return render(request,'conso/section/update_update.html',{'form':form, 'section':section})
        else:
            form = SectionForm(instance=section)
        return render(request,'conso/section/update_section.html',{'form':form,'section':section})
    except Exception as e:
        # Gérer l'exception, par exemple, rediriger vers une page d'erreur
        return render(request, 'conso/error.html', {'error_message': str(e)})

#Supprimer une section
@login_required
def delete_section(request, pk):
    try:
        section = Section.objects.get(id=pk)
        if request.method=="POST":
            section.delete()
            return redirect('section')
        context={'item':section}
        return render(request,'conso/section/delete_section.html',context)
    except Exception as e:
        # Gérer l'exception, par exemple, rediriger vers une page d'erreur
        return render(request, 'conso/error.html', {'error_message': str(e)})

#Details sur une section
@login_required
def detail_section(request, pk):
    try:
        section = Section.objects.get(id=pk)
        dispos = Dispositif.objects.filter(section=section)
        consom_by_dispositif = []
        #determination du jour
        today = date.today()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        #Determination de la semaine
        thisday = datetime.today()
        start_of_week = thisday - timedelta(days=thisday.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        #Determination du mois
        month_start = today.replace(day=1)
        next_month = month_start.replace(month=month_start.month % 12 + 1, year=month_start.year + month_start.month // 12)
        month_end = next_month - timedelta(days=1)
        for dispo in dispos:
            total_consommation_dispositif = Consommation.objects.filter(dispositif=dispo).aggregate(Sum('quantite'))['quantite__sum']
            if total_consommation_dispositif is None:
                total_consommation_dispositif = 0
            #Consommation par jour
            daily_consommation_dispositif = Consommation.objects.filter(dispositif=dispo,created_at__range=(start_of_day, end_of_day)).aggregate(Sum('quantite'))['quantite__sum']
            if daily_consommation_dispositif is None:
                daily_consommation_dispositif = 0
            weekly_consommation_dispositif = Consommation.objects.filter(dispositif=dispo,
                created_at__date__range=[start_of_week, end_of_week]
            ).values('created_at__date').aggregate(Sum('quantite'))['quantite__sum']        
            if weekly_consommation_dispositif is None:
                weekly_consommation_dispositif = 0
            monthly_consommation_dispositif = Consommation.objects.filter(dispositif=dispo, created_at__range=(month_start, month_end)).aggregate(Sum('quantite'))['quantite__sum']
            if monthly_consommation_dispositif is None:
                monthly_consommation_dispositif = 0
            consom_by_dispositif.append({
                    'dispositif': dispo,
                    'total_consommation_dispositif': total_consommation_dispositif,
                    'daily_consommation_dispositif': daily_consommation_dispositif,
                    'weekly_consommation_dispositif': weekly_consommation_dispositif,
                    'monthly_consommation_dispositif': monthly_consommation_dispositif,
                })
        actuel = {
            'section': section,
            'consom_by_dispositif': consom_by_dispositif,
        }    
        return render(request, 'conso/section/detail_section.html', actuel) 
    except Exception as e:
        # Gérer l'exception, par exemple, rediriger vers une page d'erreur
        return render(request, 'conso/error.html', {'error_message': str(e)})


##### Accès vers la vue des dispositifs
#Accès vers la liste des dispositifs
@login_required
def dispo(request):
    try:
        client = request.user
        dispos = Dispositif.objects.filter(section__entreprise__user=client)
        return render(request,'conso/dispositif/dispo.html',{'dispos':dispos})
    except Exception as e:
        # Gérer l'exception, par exemple, rediriger vers une page d'erreur
        return render(request, 'conso/error.html', {'error_message': str(e)})

#Ajout d'un nouveau dispositf
@login_required
def add_dispo(request, section_pk):
    try:
        section = Section.objects.get(id=section_pk)
        if request.method == "POST":
            form=DispositifForm(request.POST)
            if form.is_valid():
                dispo=form.save(commit=False)
                dispo.section=section
                dispo.save()
                dispo_enr = form.cleaned_data.get('nom_lieu')
                return redirect('section')
            else:
                return render(request,'conso/dispositif/add_dispositif.html',{'form':form})
        else:
            initial_data = {'section': section.id}
            form = DispositifForm(initial=initial_data)
        return render(request,'conso/dispositif/add_dispositif.html',{'form':form})
    except Exception as e:
        # Gérer l'exception, par exemple, rediriger vers une page d'erreur
        return render(request, 'conso/error.html', {'error_message': str(e)})

#Modifier un dispositif
@login_required
def update_dispo(request, pk):
    try:
        dispo = Dispositif.objects.get(id=pk)
        form=DispositifForm(instance=dispo)
        if request.method=="POST":
            form = DispositifForm(request.POST, instance=dispo)
            if form.is_valid():
                form.save()
                return redirect('section')
            else:
                return render(request,'conso/dispositif/update_dispositif.html',{'form':form,'dispo':dispo})
        return render(request,'conso/dispositif/update_dispositif.html',{'form':form,'dispo':dispo})
    except Exception as e:
        # Gérer l'exception, par exemple, rediriger vers une page d'erreur
        return render(request, 'conso/error.html', {'error_message': str(e)})

#Supprimer un dispositif
@login_required
def delete_dispo(request, pk):
    try:
        dispo = Dispositif.objects.get(id=pk)
        if request.method == "POST":
            dispo.delete()
            return redirect('section')
        context={'item':dispo}
        return render(request,'conso/dispositif/delete_dispositif.html',context)
    except Exception as e:
        # Gérer l'exception, par exemple, rediriger vers une page d'erreur
        return render(request, 'conso/error.html', {'error_message': str(e)})


##### Accès vers la vue de FAQ
def faq(request):
    return render(request,'conso/faq.html')

##### Accès vers la vue d'inscription sur la plateforme
def register(request):
    form = forms.UserRegistrationForm()
    if request.method == 'POST':
        form = forms.UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Entreprise.objects.create(user=user)
            # auto-login user
            login(request, user)
            return redirect('login')
    return render(request, 'conso/profil/register.html', context={'form': form})


#### Accès vers la vue de connexion
def login_views(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request,username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            return redirect('login')
    return render(request, 'conso/profil/login.html')


##### Accès vers la vue de deconnexion
@login_required
def logout_views(request):
    logout(request)
    return redirect('login')


##### Accès vers la vue du profil utilisateur
@login_required(login_url='login')
def profil_views(request):
    entreprise = Entreprise.objects.get(user=request.user)
    consommation = Consommation.objects.filter(dispositif__section__entreprise=entreprise).aggregate(Sum('quantite'))['quantite__sum']
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=request.user)
        entreprise_form = EntrepriseForm(request.POST, instance=request.user.entreprise)
        
        if user_form.is_valid() and entreprise_form.is_valid():
            user_form.save()
            entreprise_form.save()
            return redirect('profil')
    else:
        user_form = UserProfileForm(instance=request.user)
        entreprise_form = EntrepriseForm(instance=request.user.entreprise)
    context = {
        'entreprise': entreprise,
        'consommation': consommation,
        'user_form': user_form,
        'entreprise_form': entreprise_form,
    }
    
    return render(request, 'conso/profil/profil_views.html', context)

####Accès vers la vue de la modification du mot de passe
@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Mettre à jour la session de l'utilisateur pour éviter la déconnexion
            update_session_auth_hash(request, user)
            return redirect('profil')  # Rediriger vers la page de profil ou une autre page de confirmation
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'conso/profil/password.html', {'form': form})


#####Accès aux vues vers le calcul de la consommation

@login_required
def consoDispo(request):
    try:
        dispos = Dispositif.objects.all()
        consDis = []
        for dispo in dispos:
            Consom = Consommation.objects.filter(dispositif=dispo).aggregate(Sum('quantite'))['quantite__sum']
            consDis.append({'dispositif': dispo, 'total_consommation': Consom})
        
        tera = {'consommation_par_dispositif': consDis}
        return render(request, 'consommation_par_dispositif.html', tera)
    except Exception as e:
        # Gérer l'exception, par exemple, rediriger vers une page d'erreur
        return render(request, 'conso/error.html', {'error_message': str(e)})

##### Accès vers la vue des historiques
# Historique consommation générale
def historique(request):
    user_id = request.user.id
    user_entreprise_id = get_object_or_404(Entreprise, user_id=user_id)
    mega = {}

    if request.method == 'POST':
        date_debut_str = request.POST.get('date_debut')
        date_fin_str = request.POST.get('date_fin')
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()

        if 'download' in request.POST:
            # Traitement pour le téléchargement
            consommations = Consommation.objects.filter(dispositif__section__entreprise=user_entreprise_id, created_at__range=(date_debut, date_fin))
            daily_totals = defaultdict(float)
            for consommation in consommations:
                date = consommation.created_at.date()
                key = (date, consommation.dispositif.source_eau, consommation.dispositif.nom_lieu, consommation.dispositif.section.nom_section)
                daily_totals[key] += consommation.quantite

            response = HttpResponse(content_type='application/ms-excel')
            response['Content-Disposition'] = 'attachment; filename="consommation_eau.xlsx"'
            workbook = openpyxl.Workbook()
            worksheet = workbook.active

            headers = ['Date', 'Nom Lieu', 'Nom Section', 'Source d\'Eau', 'Quantité']
            worksheet.append(headers)

            for key, total in daily_totals.items():
                date, source_eau, nom_lieu, nom_section = key
                row = [date, nom_lieu, nom_section, source_eau, total]
                worksheet.append(row)

            workbook.save(response)
            return response
        else:
                # Statistique descriptive quotidienne
            consommation_totale = Consommation.objects.filter(dispositif__section__entreprise=user_entreprise_id, created_at__range=(date_debut, date_fin))
            df_consommation = pd.DataFrame(list(consommation_totale.values()))

            # Convertissez la colonne 'created_at' en type datetime
            df_consommation['created_at'] = pd.to_datetime(df_consommation['created_at'])

            # Regroupez les données par jour et calculez les statistiques
            daily_stats = df_consommation.groupby(df_consommation['created_at'].dt.date).agg({
                'quantite': ['mean', 'sum', 'min', 'max']
            })
            daily_stats.columns = ['Moyenne quotidienne', 'Total quotidien', 'Minimum quotidien', 'Maximum quotidien']
            daily_stats.reset_index(inplace=True)

            # Trouvez le jour avec la consommation minimale et maximale
            min_day = daily_stats[daily_stats['Total quotidien'] == daily_stats['Total quotidien'].min()]
            max_day = daily_stats[daily_stats['Total quotidien'] == daily_stats['Total quotidien'].max()]

            # Récupérez la date et la quantité correspondantes
            min_date = min_day['created_at'].iloc[0]
            min_quantity = min_day['Total quotidien'].iloc[0]
            max_date = max_day['created_at'].iloc[0]
            max_quantity = max_day['Total quotidien'].iloc[0]

            moyenne = df_consommation['quantite'].mean()  # Moyenne globale
            total = df_consommation['quantite'].sum()    # Total globale

            moyenne_formatted = "{:.2f}".format(moyenne)
            total_formatted = "{:.2f}".format(total)
            min_val_formatted = "{:.2f}".format(min_quantity)
            max_val_formatted = "{:.2f}".format(max_quantity)

        context = {
            'moyenne': moyenne_formatted,
            'total': total_formatted,
            'min_date': min_date,
            'min_val': min_val_formatted,
            'max_date': max_date,
            'max_val': max_val_formatted,
            'daily_stats': daily_stats.to_dict(orient='records'),
        }

        mega = {
            'context': context,
            'date_debut': date_debut,
            'date_fin': date_fin,
        }

    return render(request, 'conso/suivi/historique.html', {'mega': mega})

def ConsDispo(request,pk):
    dispositif = Dispositif.objects.get(id=pk)
    dispos = Dispositif.objects.all()
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    #determination du jour
    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    month_start = today.replace(day=1)
    next_month = month_start.replace(month=month_start.month % 12 + 1, year=month_start.year + month_start.month // 12)
    month_end = next_month - timedelta(days=1)
    thisday = date.today()
    start_of_week = thisday - timedelta(days=thisday.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    #Consommation du jour
    daily_consommation = (Consommation.objects
                          .filter(dispositif=dispositif,created_at__range=(start_of_day, end_of_day))
                          .aggregate(Sum('quantite'))['quantite__sum'])
    if daily_consommation is None:
        daily_consommation = 0

    #determination de la consommation de la semaine
    weekly_consommation = (Consommation.objects
                            .filter(dispositif=dispositif,created_at__range=(start_of_week, end_of_week))
                            .aggregate(Sum('quantite'))['quantite__sum'])
    if weekly_consommation is None:
        weekly_consommation = 0 
    #Consommation du mois
    monthly_consommation = (Consommation.objects
                                  .filter(dispositif=dispositif,created_at__range=(month_start, month_end))
                                  .aggregate(Sum('quantite'))['quantite__sum'])
    if monthly_consommation is None:
        monthly_consommation = 0
    #Consommation des 07 derniers
    data = (
            Consommation.objects
            .filter(dispositif=dispositif,created_at__range=(start_date, end_date))
            .values('created_at__date')
            .annotate(quantite_sum=Sum('quantite'))
        )
    data_list = [{'day': item['created_at__date'], 'quantite_sum': item['quantite_sum']} for item in data]
    ahmed = {'data': data_list,
             "dispositif":dispositif,
             "dispos":dispos,
             "today":today,
             "daily_consommation":daily_consommation,
             "weekly_consommation":weekly_consommation,
             "monthly_consommation":monthly_consommation,
            }
    return render(request,'conso/consommation/dispositif.html',ahmed)



def ConsSection(request, pk):
    section = Section.objects.get(id=pk)
    sections = Section.objects.all()
    dispositifs = Dispositif.objects.filter(section=section)
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    #determination du jour
    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    month_start = today.replace(day=1)
    next_month = month_start.replace(month=month_start.month % 12 + 1, year=month_start.year + month_start.month // 12)
    month_end = next_month - timedelta(days=1)
    thisday = date.today()
    start_of_week = thisday - timedelta(days=thisday.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    data = []
    #Consommation du jour
    daily_consommation = Consommation.objects.filter(dispositif__section=section,created_at__range=(start_of_day, end_of_day)).aggregate(Sum('quantite'))['quantite__sum']
    if daily_consommation is None:
        daily_consommation = 0
    #determination de la consommation de la semaine
    weekly_consommation = (Consommation.objects
                            .filter(dispositif__section=section,created_at__range=(start_of_week, end_of_week))
                            .aggregate(Sum('quantite'))['quantite__sum'])
    if weekly_consommation is None:
        weekly_consommation = 0 
    #Consommation du mois
    monthly_consommation = (Consommation.objects
                            .filter(dispositif__section=section,created_at__range=(month_start, month_end))
                            .aggregate(Sum('quantite'))['quantite__sum'])
    if monthly_consommation is None:
        monthly_consommation = 0
    #Consommation des 07 derniers jours
    data = (
            Consommation.objects
            .filter(dispositif__section=section,created_at__range=(start_date, end_date))
            .values('created_at__date')
            .annotate(quantite_sum=Sum('quantite'))
        )
    data_list = [{'day': item['created_at__date'], 'quantite_sum': item['quantite_sum']} for item in data]
    #Consommation des 12 derniers mois
    daily_consommation_dispositif = []
    weekly_consommation_dispositif = []
    monthly_consommation_dispositif = []

    for dispo in dispositifs:
        monthly_consommation_dispositif.append(Consommation.objects.filter(dispositif=dispo, created_at__range=(month_start, month_end)).aggregate(Sum('quantite'))['quantite__sum'])
        weekly_consommation_dispositif.append(Consommation.objects.filter(dispositif=dispo, created_at__range=(start_of_week, end_of_week)).aggregate(Sum('quantite'))['quantite__sum'])
        daily_consommation_dispositif.append(Consommation.objects.filter(dispositif=dispo, created_at__range=(start_of_day, end_of_day)).aggregate(Sum('quantite'))['quantite__sum'])
    rachid = {'data': data_list,
              "section":section,
              "sections":sections,
              "dispositifs":dispositifs,
              "today":today,
              "daily_consommation":daily_consommation,
              "weekly_consommation":weekly_consommation,
              "monthly_consommation":monthly_consommation,
              "daily_consommation_dispositif":daily_consommation_dispositif,
              "weekly_consommation_dispositif":weekly_consommation_dispositif,
              "monthly_consommation_dispositif":monthly_consommation_dispositif,
               }
    return render(request,'conso/consommation/section.html',rachid)



def prevision(request):
    # 1. Obtenez toutes les données de consommation pour l'utilisateur connecté
    user_id = request.user.id
    user_entreprise_id = get_object_or_404(Entreprise, user_id=user_id)
    consommations = Consommation.objects.filter(dispositif__section__entreprise=user_entreprise_id)
    if not consommations:
        return None, None
    # 2. Agrégez les données de consommation par jour (sommation)
    consommations_par_jour = consommations.values('created_at__date').annotate(total_consommation=Sum('quantite'))
    # 3. Créez un DataFrame pandas à partir des données agrégées
    df = pd.DataFrame(consommations_par_jour)
    df.set_index('created_at__date', inplace=True)
    # 4. Analyse préliminaire de la série temporelle
    tendance = tendance = df.rolling(window=7).mean()  # Calcul de la tendance (par exemple, moyenne mobile)
    saisonnalite_hebdo = df - tendance  
    #Test de Duckey Fuller augmente
    result = sm.tsa.adfuller(saisonnalite_hebdo.dropna())
    p_value = result[1]
    if p_value < 0.05:
        has_trend_seasonality = True
    else:
        has_trend_seasonality = False
    
    if has_trend_seasonality:
    # Lissage exponentiel double (Holt-Winters) pour les séries avec tendance et saisonnalité
        model = sm.tsa.ExponentialSmoothing(df, seasonal='add', seasonal_periods=7, trend='add')
        fitted = model.fit()
    else:
    # Lissage exponentiel simple pour les séries sans tendance ni saisonnalité
        model = sm.tsa.ExponentialSmoothing(df, trend=None, seasonal=None)
        fitted = model.fit()

    residuals = df - fitted.fittedvalues
    steps=2
    forecast = fitted.forecast(steps=steps)
    if len(residuals) > 0 and isinstance(residuals.iloc[-1], (int, float)):
        prevision = forecast + residuals.iloc[-1]
    else :
        prevision = forecast

    return render(request, "conso/suivi/prevision.html",{"forecast":prevision})


def prevision_section(request,pk):
    # 1. Obtenez toutes les données de consommation pour l'utilisateur connecté
    section = Section.objects.get(id=pk)
    consommations = Consommation.objects.filter(dispositif__section=section)
    if not consommations:
        return None, None
    # 2. Agrégez les données de consommation par jour (sommation)
    consommations_par_jour = consommations.values('created_at__date').annotate(total_consommation=Sum('quantite'))
    # 3. Créez un DataFrame pandas à partir des données agrégées
    df = pd.DataFrame(consommations_par_jour)
    df.set_index('created_at__date', inplace=True)
    # 4. Analyse préliminaire de la série temporelle
    tendance = tendance = df.rolling(window=7).mean()  # Calcul de la tendance (par exemple, moyenne mobile)
    saisonnalite_hebdo = df - tendance  
    #Test de Duckey Fuller augmente
    result = sm.tsa.adfuller(saisonnalite_hebdo.dropna())
    p_value = result[1]
    if p_value < 0.05:
        has_trend_seasonality = True
    else:
        has_trend_seasonality = False
    if has_trend_seasonality:
    # Lissage exponentiel double (Holt-Winters) pour les séries avec tendance et saisonnalité
        model = sm.tsa.ExponentialSmoothing(df, seasonal='add', seasonal_periods=7, trend='add')
        fitted = model.fit()
    else:
    # Lissage exponentiel simple pour les séries sans tendance ni saisonnalité
        model = sm.tsa.ExponentialSmoothing(df, trend=None, seasonal=None)
        fitted = model.fit()
    residuals = df - fitted.fittedvalues
    steps=2
    forecast = fitted.forecast(steps=steps)
    if len(residuals) > 0 and isinstance(residuals.iloc[-1], (int, float)):
        prevision = forecast + residuals.iloc[-1]
    else :
        prevision = forecast

    return render(request, "conso/suivi/prevision_section.html",{"forecast":prevision})

def prevision_dispo(request,pk):
    # 1. Obtenez toutes les données de consommation pour l'utilisateur connecté
    dispo=Dispositif.objects.get(id=pk)
    consommations = Consommation.objects.filter(dispositif=dispo)
    if not consommations:
        return None, None
    # 2. Agrégez les données de consommation par jour (sommation)
    consommations_par_jour = consommations.values('created_at__date').annotate(total_consommation=Sum('quantite'))
    # 3. Créez un DataFrame pandas à partir des données agrégées
    df = pd.DataFrame(consommations_par_jour)
    df.set_index('created_at__date', inplace=True)
    # 4. Analyse préliminaire de la série temporelle
    tendance = tendance = df.rolling(window=7).mean()  # Calcul de la tendance (par exemple, moyenne mobile)
    saisonnalite_hebdo = df - tendance  
    #Test de Duckey Fuller augmente
    result = sm.tsa.adfuller(saisonnalite_hebdo.dropna())
    p_value = result[1]

    if p_value < 0.05:
        has_trend_seasonality = True
    else:
        has_trend_seasonality = False
    
    if has_trend_seasonality:
    # Lissage exponentiel double (Holt-Winters) pour les séries avec tendance et saisonnalité
        model = sm.tsa.ExponentialSmoothing(df, seasonal='add', seasonal_periods=7, trend='add')
        fitted = model.fit()
    else:
    # Lissage exponentiel simple pour les séries sans tendance ni saisonnalité
        model = sm.tsa.ExponentialSmoothing(df, trend=None, seasonal=None)
        fitted = model.fit()
    
    residuals = df - fitted.fittedvalues
    steps=2
    forecast = fitted.forecast(steps=steps)
    if len(residuals) > 0 and isinstance(residuals.iloc[-1], (int, float)):
        prevision = forecast + residuals.iloc[-1]
    else :
        prevision = forecast

    return render(request, "conso/suivi/prevision_dispo.html",{"forecast":prevision})






class ConsommationViewset(ModelViewSet): 
    serializer_class = ConsommationSerializer
    def get_queryset(self):
        return Consommation.objects.all()

def budget(request):
    user = request.user
    user_entreprise = get_object_or_404(Entreprise, user=user)
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    end_of_month = start_of_month.replace(day=1) + timedelta(days=32)
    end_of_month = end_of_month - timedelta(days=end_of_month.day)
    start_of_period = datetime.combine(start_of_month, datetime.min.time())
    end_of_period = datetime.combine(end_of_month, datetime.max.time())
    
    total_consommation = (Consommation.objects
                                .filter(dispositif__source_eau="ONEA", dispositif__section__entreprise=user_entreprise, created_at__range=(start_of_period, end_of_period))
                                .aggregate(Sum('quantite'))['quantite__sum'] or Decimal('0'))
    montant_consommation = Decimal('500') * Decimal(total_consommation)

    budget_obj = None
    budget_defini = False

    try:
        budget_obj = Budget.objects.get(entreprise=user_entreprise)
        montant_budget_total = budget_obj.montant
        budget_defini = True
    except Budget.DoesNotExist:
        montant_budget_total = Decimal('0')
        budget_defini = False

    montant_commande_total = Decimal(request.session.get('montant_commande', '0'))

    # Calcul du total des dépenses pour l'entreprise
    total_depenses = (Depense.objects
                     .filter(entreprise=user_entreprise)
                     .aggregate(Sum('montant'))['montant__sum'] or Decimal('0'))

    if request.method == 'POST':
        if 'budget' in request.POST:
            montant_budget = Decimal(request.POST['budget'])
            budget_defini = True

            if budget_obj:
                budget_obj.montant += montant_budget
                budget_obj.save()
            else:
                budget_obj = Budget.objects.create(entreprise=user_entreprise, montant=montant_budget)

            # Mettez à jour le budget dans la session
            request.session['montant_budget'] = str(montant_budget)

            messages.success(request, f"Le budget a été mis à jour. Nouveau budget total: {montant_budget}")
        
        elif 'commande' in request.POST:
            montant_commande = Decimal(request.POST['montant_commande'])
            montant_commande_total += montant_commande
            request.session['montant_commande'] = str(montant_commande_total)
            messages.success(request, f"Le montant de la commande a été mis à jour. Nouveau montant total: {montant_commande_total}")

    reste_budget = montant_budget_total - (montant_consommation + montant_commande_total + total_depenses)

    seuils = [30, 50, 70, 80, 90, 95, 99, 100, 101]

    alertes = {}
    for seuil in seuils:
        if total_consommation <= Decimal(seuil):
            alertes[seuil] = f"Consommation inférieure ou égale à {seuil}%"
        else:
            alertes[seuil] = f"Consommation supérieure à {seuil}%"

    context = {
        'budget_defini': budget_defini,
        'montant_budget': montant_budget_total,
        'period_consommation': total_consommation,
        'montant_consommation': montant_consommation,
        'montant_commande': montant_commande_total,
        'total_depenses': total_depenses,  # Ajoutez le total des dépenses au contexte
        'reste_budget': reste_budget,
        'alertes': alertes,
        "start_of_period": start_of_period,
        "end_of_period": end_of_period,
    }
    return render(request, 'conso/suivi/budget.html', context)



def fuite(request):
    client = request.user
    sections = Section.objects.filter(entreprise__user=client)
    return render(request,'conso/suivi/fuite.html',{"sections":sections})

def fuite_section(request, pk):
    section = Section.objects.get(id=pk)
    total_consommation = 0  # Initialisation du total à zéro par défaut
    heure_debut = None  # Initialisation de l'heure de début
    heure_fin = None
    
    if request.method == 'POST':
        heure_debut_str = request.POST['heure_debut']
        heure_fin_str = request.POST['heure_fin']

        # Convertissez les chaînes en objets datetime
        heure_debut = datetime.strptime(heure_debut_str, '%H:%M')
        heure_fin = datetime.strptime(heure_fin_str, '%H:%M')

        # Utilisez les objets datetime pour filtrer les enregistrements de consommation
        total_consommation = (Consommation.objects
                                .filter(dispositif__section=section, created_at__range=(heure_debut, heure_fin))
                                .aggregate(Sum('quantite'))['quantite__sum'])

        if total_consommation is None:
            total_consommation = 0

        if total_consommation > 0:
            message_alerte = f"Alerte de fuite dans la section {section.nom_section}. Au consommation de {total_consommation} litres a été enregistree."
            alert = Alert(intitule="Fuite", message=message_alerte)
            alert.save()

    context={
        "section": section,
        "total_consommation": total_consommation,
        "heure_debut":heure_debut,
        "heure_fin":heure_fin,
        }
    return render(request, 'conso/suivi/fuite_section.html', context)


def alert(request):
    alerts = Alert.objects.filter(is_read=False).order_by('-date')  # Obtenez les alertes non lues et triez-les par date décroissante
    return render(request, 'conso/alert.html', {'alerts': alerts})

def read_alert(request, pk):
    alert = get_object_or_404(Alert, id=pk)
    alert.is_read = True
    alert.save()
    return render(request, 'conso/lecture.html', {'alert': alert})