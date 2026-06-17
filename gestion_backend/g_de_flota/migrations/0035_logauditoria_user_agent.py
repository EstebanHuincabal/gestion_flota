from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0034_dashboard_permisos_por_categoria'),
    ]

    operations = [
        migrations.AddField(
            model_name='logauditoria',
            name='user_agent',
            field=models.TextField(blank=True, null=True),
        ),
    ]
