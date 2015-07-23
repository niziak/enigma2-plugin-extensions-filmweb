[English Version](Welcome.md)



---


# Wprowadzenie #

---

Plugin został przygotowany w PYTHON-ie i działa w środowisku ENIGMA2 zainstalowanym na STB. Działanie polega na wyszukiwaniu informacji dotyczących filmów i seriali z EPG w portalu Filmweb i wyświetlaniu tych informacji na ekranie telewizora. W przypadku, gdy rezultatem wyszukiwania jest więcej niż jeden wynik plugin umożliwia wybór odpowiedniej pozycji z menu. Użytkownik dostaje pełną informację o filmie czy serialu czyli tytuł, tytuł oryginalny, rok produkcji, czas trwania, opis skrócony, opisy, plakat itp. Plugin umożliwia również zalogowanie do portalu i wykonanie operacji dostępnych dla zalogowanego użytkownika takich jak własna ocena.


# Instalacja #

---

  * Zaloguj się do dreambox-a przez SSH czy Telnet
  * Usuń poprzednią wersję pluginu - niekonieczne ale zalecane
```
opkg remove enigma2-plugin-extensions-filmweb
```
  * Zainstaluj biblioteki: python-html, python-twisted-web, openssl, python-pyopenssl
```
opkg update
opkg install python-html
opkg install python-twisted-web
opkg install openssl
opkg install python-pyopenssl
```
  * Skopiuj plik IPK do katalogu /tmp
  * Wykonaj manulaną instalację pakietu IPK z menu dreamboxa
```
opkg install /tmp/enigma2-plugin-extensions-filmweb_1.2.8.5_mips32el.ipk
```
  * Restart Enigmy
```
init 4; sleep 10; init 3;
```


# Sposób użycia #

---

Możesz uruchomić plugin z dwóch miejsc:
  * z Menadżera Pluginów - automatycznie wyszukuje informacje o aktualnie oglądanym programie
  * z menu na długim naciśnięciu INFO / EPG - tutaj wyświetlana jest lista wyboru kanału

Ja osobiście zainstalowałem sobie skrót na naciśnięciu ŻÓŁTEGO klawisza przy użyciu plugina MultiQuickButton.

[Szczegółowy opis opcji pluginu](Opcje.md)

# Opis włączenia logów dla Enigma2 #

---

  * Zaloguj się do BOXa uzywając Telnet lub SSH
  * Zatrzymaj Enigmę komendą:
```
killall -9 enigma2
```
  * Wystartuj Enigmę z logowaniem do pliku:
```
/usr/bin/enigma2 > /tmp/enigma2_logfile.log 2>&1
```
  * Wykonaj odpowiednie akcje, aby zapisały się dane do logu
  * Zrestartuj Enigmę w trybie usługi:
```
killall -9 enigma2
init 4; sleep 10; init 3
```


# Informacja o zmianach w wersjach #

---

### ver. 1.2.8 (2013/08/11) ###
  * Nowa skóra autorstwa Tytus77
  * Poprawa ładowania informacji w pluginie
  * Dostosowanie do zmian w portalu filmweb
  * Poprawa problemu ze skinem - zgłoszenie pio777

---

### ver. 1.2.7 (2013/07/26) ###
  * Poprawka działania ładowania skóry pluginu
  * Poprawa ładowania czcionek dla pluginu
  * Dostosowanie do zmian w portalu filmweb

### ver. 1.2.6 (2013/07/16) ###
  * Modyfikacja skóry
  * Poprawa trafności wyszukiwania bezpośredniego oraz rozróżniania seriali od filmów dla silnika FILMWEB
  * Poprawa mapowania kanałów w service.dat
  * zmiana domyślnego silnika do pobierania EPG z Filmweb na Telemagazyn
  * Dodanie definicji skóry z nowymi fontami
  * Poprawa nowego pluginu - skóra + dodatkowe funkcjonalności
  * Poprawki w wyświetlaniu elementów na ekranach

### ver. 1.2.5 (2013/07/05) ###
  * Poprawki działania przełączenia pomiędzy silnikami w aplikacji
  * Poprawa pobierania tytułu oryginalnego dla silnika IMDB
  * Dodanie prezentacji informacji w formie okienka o tym, że na jednym z wybranych w Przewodniku kanałów będzie do 10 min. lub jest obecnie wyświetlany film oznaczony na portalu Filmweb jako "chcę obejrzeć" (opcja dostępna jedynie dla zalogowanych użytkowników - podany login i hasło w konfiguracji)
  * Dodanie dodatkowego pluginu pozwalającego na wyświetlenie w oknie pozycji filmowych aktualnie prezentowanych na wybranych w Przewodniku kanałach (skrócona wersja przewodnika pokazująca tylko zdarzenia aktywne w danej chwili)

### ver. 1.2.4 ###
  * Poprawka obsługi cache-a - poprawka zmienia zapis całości plików w miejsce określone konfiguracją
  * Poprawa wyświetlania godziny na zegarku w Przewodniku
  * Poprawki w działaniu zmiany silnika wyszukiwania
  * Poprawa wyświetlania informacji o własnej ocenie dla filmu dla silnika Filmweb
  * Poprawa pobierania fotosów dla filmu dla silnika Filmweb
  * Dodanie czyszczenia cache na wyjściu z okna wyszukiwarki
  * Poprawa trafności wyszukiwania bezpośredniego oraz rozróżniania seriali od filmów
  * Dodanie obsługi seriali w Przewodniku Filmowym

### ver. 1.2.3 ###
  * Poprawa działania na OpenPLI 3.0 ze skinem MetrixHD (problem zgłoszony przez JK32)
  * Poprawa mapowania serwisów na podstawie pliku konfiguracyjnego dla wyszukiwania informacji w Przewodniku Filmowym (problem zgłoszony przez JK32)

### ver. 1.2.2 ###
  * Dodanie parsowania Reżysera, Scenarzysty i Kraju dla informacji z IMDB
  * Poprawa listy serwisów dla Przewodnika Filmowego po wejściu NC+

### ver. 1.2.1 ###
  * Dostosowanie do zmian na stronie wyszukiwania Filmweb

### ver. 1.2.0 ###
  * Dodanie konfiguracji wyboru silnika wyszukiwania (Filmweb lub IMDB)
  * Dodanie wyszukiwania informacji z IMDB
  * Dodanie opcji przechodzenia pomiędzy IMDB oraz Filmweb - klawisz '>'

### ver. 1.1.6 ###
  * poprawa wyświetlania opisów
  * dodanie pobrania pełnej listy aktorów po naciśnięciu klawisza '0'

### ver. 1.1.5 ###
  * Poprawa działania Przewodnika Filmowego dla wersji Blackhole 1.7.9 (poprawka związana ze zmianą domyślnego skina)

### ver. 1.1.4 ###
  * Dodanie usuwania elementów z cache po 1 dniu
  * Dodanie pobierania informacji o ocenie z portalu IMDB - przełączanie w Przewodniku klawiszem "<" pomiędzy oceną Filmweb i IMDB (Żeby pobrać oceny z IMDB należy włączyć w konfiguracji pobieranie oceny IMDB)
### ver. 1.1.3 ###
  * Poprawki w programowaniu timera
  * Poprawki w wyświetlaniu informacji o serialach
### ver. 1.1.2 ###
  * Poprawki w parsowaniu informacji z Filmweb po zmianach na stronie
### ver. 1.1.1 ###
  * Poprawki błędów w Przewodniku Filmowym
### ver. 1.1.0 ###
  * Dodanie kombajnu o nazwie Przewodnik Filmowy, który służy do przedstawienia pozycji filmowych na wybranych kanałach wraz z oceną i opisem ściągniętym z Filmweb-u
  * Umożliwienie sortowania w przewodniku po ocenie, dacie produkcji, nazwie pozycji czy nazwie kanału
  * Umożliwienie przejścia do oglądania pozycji czy dodania / usunięcia Timera
  * Wprowadzenie poprawek i fixów działania
  * Wprowadzenie odpowiedniej obsługi dla skórek innych niż domyślna dla BlackHola
  * Dodanie pokazywania informacji o rekomendacjach z Filmweb
  * Zmiana sposobu wprowadzania własnej oceny filmu na wybór pozycji zamiast wpisywania wartości liczbowej
### ver. 1.0.9 ###
  * Series data fetching added
  * New entry for searching TV Series added to context menu in main window
  * Configuration entry added to the context menu
  * Login to portal based on the configuration data implemented
  * Added voting function entry to the context menu
  * Wallpapers fetching added
  * Some improvements and fixes
### ver. 1.0.8 ###
  * Switching to version UNK and MIPSEL
### ver. 1.0.7 ###
  * Seraching by current event and by event from EPG fixed
  * Runtime parsing fixed - changes on the Filmweb.pl page
### ver. 1.0.6 ###
  * Added Left/Right key actions handling on Details page to enable scrolling cast list or plot list
  * Query screen changed - added rating and other info
### ver. 1.0.5 ###
  * Dependency fixed ininstallation script
### ver. 1.0.4 ###
  * Added extra menu on the CTX-MENU button
  * Color buttons look redesigned
  * GUI changed
  * Cast list changed - actor pictures showing added
  * Movie runtime showing added
  * Added actions on main window context menu
    * action for enter the movie name to search
    * action for channel selection from EPG
  * Fixed swiching button labels regarding the active context

### ver. 1.0.3 ###
  * when the result list has 0 elements the input box is showed
### ver. 1.0.2 ###
  * fixed cookies handling - the Filmweb.pl shows the adverts and checks when advs are read by checking the cookies
  * fixed handling DETAILS page when there are 0 movies in menu
### ver. 1.0.1 ###
build scripts fixed so the binary installation package is deployable now
### ver. 1.0 ###
the first release