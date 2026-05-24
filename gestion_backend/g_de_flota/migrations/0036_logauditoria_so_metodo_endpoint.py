from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0035_logauditoria_user_agent'),
    ]

    operations = [
        migrations.AddField(
            model_name='logauditoria',
            name='so',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='logauditoria',
            name='metodo',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='logauditoria',
            name='endpoint',
            field=models.CharField(blank=True, max_length=300, null=True),
        ),
    ]
