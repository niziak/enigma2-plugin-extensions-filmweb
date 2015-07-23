[Strona główna](Witam.md)



---

## Ekran wyboru pozycji z EPG ##
Wciśnij klawisz EPG długo a zostanie wyświetlony ekran wyboru pozycji na bieżącym kanale - patrz obrazek niżej. Potem wybierz pozycję która Cię interesuje i wciśnij CZERWONY, a przejdziesz do prezentacji informacji o wybranej pozycji - patrz obrazek niżej.

<table cellpadding='2' cellspacing='2' border='0'>
<tbody><tr valign='top'><td><img src='http://enigma2-plugin-extensions-filmweb.googlecode.com/svn/wiki/EPG-SEL-SCREEN.png' /></td><td><img src='http://enigma2-plugin-extensions-filmweb.googlecode.com/svn/wiki/sss-12.png' /></td></tr></tbody></table>

## Przewodnik Filmowy (Movie Guide) ##
Ustaw przeszukiwane kanały na ekranie konfiguracyjnym - patrz obrazek niżej. Wyboru dokonujesz poprzez wciśnięcie klawisza OK. Kanał zostanie podświetlony na niebiesko. Podobnie jeżeli chcesz odznaczyć na zaznaczonym kanale naciśnij OK. Wyjście z okna konfiguracji na klawiszu EXIT - konfiguracja automatycznie się zapisuje. Po skonfigurowaniu naciśnij GREEN a dostaniesz opisy filmów na wybranych kanałach - patrz obrazek niżej.

<table cellpadding='2' cellspacing='2' border='0'>
<tbody><tr valign='top'><td><img src='http://enigma2-plugin-extensions-filmweb.googlecode.com/svn/wiki/sss-13.png' /></td><td><img src='http://enigma2-plugin-extensions-filmweb.googlecode.com/svn/wiki/MG2.png' /></td></tr></tbody></table>

## Przegląd aktualnie wyświetlanych pozycji filmowych ##
Nowy plugin wyświetla liste aktualnych pozycji filmowych na wybranych w przewodniku kanałach. Po naciśnięciu OK następuje przejście do oglądania wybranej pozycji. Po naciśnięciu "0" następuje prezentacja szczegółów w oknie "Film Web 2013". Wyjście poprzez EXIT.


<table cellpadding='2' cellspacing='2' border='0'>
<tbody><tr valign='top'><td><img src='http://enigma2-plugin-extensions-filmweb.googlecode.com/svn/wiki/SH-2.png' /></td></tr></tbody></table>

## Opcje Konfiguracyjne ##

| Opcja | Znaczenie |
|:------|:----------|
| Email lub nick | Login do konta Filmweb |
| Hasło | Hasło do konta Filmweb |
| Katalog Tymczasowy | Ścieżka do katalogu z plikami tymczasowymi (cache) dla Przewodnika Filmowego |
| Poziom Logowania | Poziom logowania w logu Enigmy - debug: najbardziej szczegółowe, error: najmniej szczegółów |
| Liczba dni przy przeszukiwaniu Przewodnikiem | Określa wielkość paczki informacji pobieranych przez Przewodnik Filmowy. Jako paczkę należy rozumieć informacje o programach TV na określoną liczbę dni |
| Pobieranie danych z IMDB dla pozycji w Przewodniku | W przypadku ustawienia wartości logicznej na TRUE w trakcie pobierania informacji w Przewodniku pobierana jest również informacja o ocenie IMDB, którą można zobaczyć po przełaczniu klawiszem '<' |
| Domyślny silnik wyszukiwania | Możliwość wyboru domyślnego silnika wyszukiwania - opcje Filmweb lub IMDB |
| Pokazuj komunikaty -Chcę obejrzeć- | Określenie czy mają być pokazywane automatyczne komunikaty informujące, że na jednym z wybranych w Przewodniku kanałów będzie wyświetlany film, który jest oznaczony w Filmwebie jako "Chcę obejrzeć" |

## Opcje pluginu Filmweb ##

<table cellpadding='2' cellspacing='2' border='0'>
<tbody><tr valign='top'><td><img src='http://enigma2-plugin-extensions-filmweb.googlecode.com/svn/wiki/rc-main.png' /></td><td>

<h3>Opis klawiszy dla okna głównego</h3>

<table><thead><th> Klawisz </th><th> Znaczenie </th></thead><tbody>
<tr><td> RED     </td><td> Powoduje wyjście z pluginu </td></tr>
<tr><td> GREEN   </td><td> Pokazuje listę wyszukanych pozycji w przypadku, gdy natrafiono na więcej niż jedną w trakcie przeszukiwania bazy Filmweb </td></tr>
<tr><td> YELLOW  </td><td> Pokazuje podstawowe informacje na temat pozycji oraz przełącza tryb działania z wyszukiwania filmów na wyszukiwanie seriali </td></tr>
<tr><td> BLUE    </td><td> Przełącza widok w tryb pokazywania opisów dotyczących wyszukanej pozycji </td></tr>
<tr><td> EPG     </td><td> W tym momencie to samo co YELLOW </td></tr>
<tr><td> MENU    </td><td> Pokazuje menu kontekstowe pluginu </td></tr>
<tr><td> MOVIE   </td><td> Uruchamia okno Przewodnika Filmowego </td></tr>
<tr><td> 0       </td><td> Pobranie pełnej listy aktorów </td></tr>
<tr><td> >       </td><td> Przełączenie wyszukiwania innym silnikiem wyszukiwania niż obecny (dostępne Filmweb i IMDB) </td></tr></tbody></table>

</td></tr></tbody></table>

## Opcje Przewodnika Filmowego (Movie Guide) ##

<table cellpadding='2' cellspacing='2' border='0'>
<tbody><tr valign='top'><td><img src='http://enigma2-plugin-extensions-filmweb.googlecode.com/svn/wiki/rc-movieguide.png' /></td><td>

<h3>Opis klawiszy dla Przewodnika</h3>

<table><thead><th> Klawisz </th><th> Znaczenie </th></thead><tbody>
<tr><td> RED     </td><td> Uruchamia okno konfiguracji kanałów używanych do wyszukiwania filmów </td></tr>
<tr><td> GREEN   </td><td> Powoduje odświeżenie listy filmów - pobranie ponowne informacji o pozycjach filmowych na wybranych kanałach </td></tr>
<tr><td> YELLOW  </td><td> Pobranie następnej paczki informacji. Na wejściu plugin pobiera informacje o pozycjach w programie TV dla określonej w konfiguracji dni (domyślnie 2 dni). Po naciśnięciu żółtego klawisza doczytywane są pozycje programowe na następne 2 dni i tak dalej. </td></tr>
<tr><td> BLUE    </td><td> Powoduje zmianę pola sortowania - możliwe wartości to: tytuł, czas rozpoczęcia, rok, ocena, nazwa kanału </td></tr>
<tr><td> 0       </td><td> Zmiana sortowania z rosnącego na malejące i odwrotnie </td></tr>
<tr><td> EXIT    </td><td> Wyjście z Przewodnika do okna wywołującego </td></tr>
<tr><td> OK      </td><td> W zależności od wybranej pozycji powoduje: przejście do oglądania danej pozycji (pozycja z zielonym znakiem), ustawienie Timera (pozycja z niebieskim znakiem), skasowanie Timera (pozycja z zegarkiem) </td></tr>
<tr><td> <       </td><td> Przełącza ocenę pomiędzy IMDB i Filmweb </td></tr>
<tr><td> >       </td><td> Przełącza wyświetlanie informacji o serialach lub filmach </td></tr></tbody></table>

</td></tr></tbody></table>