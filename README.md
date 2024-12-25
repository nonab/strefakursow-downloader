# strefakursow-downloader
Prosty skrypt w pythonie do pobierania kursów z platformy strefakursow.pl

# Przed pierwszym użyciem
pip install requests pytz

# Pobieranie kursów bez podania adresu url
python strefa-kursow-downloader.py

Skrypt zaloguje się lub użyje tokena z katalogu i pobierze listę wszystkich kursów.

Nastepnie pozwoli wybrać który kurs pobrać (0 dla wszystkich, 1, 2, etc. dla pozostałych)

# Pobieranie konkretnego kursu
python strefa-kursow-downloader.py -c URL (format: https://platforma.strefakursow.pl/platforma/kurs/ID_KURSU) 

Przy pierwszym uruchomieniu skrypt poprosi o wpisanie loginu i hasła, zaloguje się i zapisze token w pliku token.json

# Pobieranie konkretnego kursu (podając token)
python strefa-kursow-downloader.py -c URL (format: https://platforma.strefakursow.pl/platforma/kurs/ID_KURSU) -t token 

Żeby zdobyć token po prostu wejdź na stronę https://platforma.strefakursow.pl/platforma/moje_kursy i w zakładce network narzędzi developerskich w filtrze wpisz 'course'.

Token znajduje się w headerze "x-platforma-token"

# Dodatkowe opcje
--save-json (zapisuje w pliku txt wszystkie odpowiedzi z api w formacie JSON)

-o nazwafolderu (nazwa folderu, w którym mają być zapisane pobierane kursy. Domyślnie 'downloads')
