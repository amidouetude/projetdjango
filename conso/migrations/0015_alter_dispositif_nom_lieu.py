# Generated by Django 4.2.4 on 2023-09-18 14:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conso', '0014_remove_question_categorie_delete_answer_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dispositif',
            name='nom_lieu',
            field=models.CharField(blank=True, choices=[('ONEA', 'ONEA'), ('Forage', 'Forage')], max_length=100, null=True, verbose_name='Le lieu où se trouve le dispositif'),
        ),
    ]
