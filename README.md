# strefakursow-downloader
Prosty skrypt w pythonie do pobierania kursów z platformy strefakursow.pl

# Użycie
python strefa-kursow-downloader.py -c URL (format: https://platforma.strefakursow.pl/platforma/kurs/ID_KURSU) -t token (format: 0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a)

Żeby zdobyć token po prostu wejdź na stronę https://platforma.strefakursow.pl/platforma/moje_kursy i w zakładce network narzędzi developerskich w filtrze wpisz 'course'.

Token znajduje się w headerze "x-platforma-token"
