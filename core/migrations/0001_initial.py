from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='SystemSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duplicate_search_years_back', models.PositiveIntegerField(default=3)),
                ('duplicate_similarity_threshold', models.FloatField(default=0.6)),
                ('duplicate_auto_flag_threshold', models.FloatField(default=0.8)),
                ('duplicate_algorithm', models.CharField(choices=[('HYBRID', 'Hybrid'), ('EMBEDDING', 'Embedding'), ('TFIDF', 'TF-IDF')], default='HYBRID', max_length=20)),
                ('duplicate_semantic_weight', models.FloatField(default=0.7)),
                ('duplicate_lexical_weight', models.FloatField(default=0.3)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
