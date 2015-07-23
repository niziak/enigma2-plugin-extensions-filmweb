[Polska Wersja](Witam.md)



---




---

# Introduction #

---

Plugin has been prepared in the PYTHON dev-language and works in the Enigma2 environment installed on the STB (Dreambox, VU+ etc.). This plugin does a query on Polish portal Filmweb.pl for information about movie or TV series selected in EPG and shows the info in a popup window on TV screen. When the query returns the ambigous results the list of possible choices is presented on TV screen so user can select correct movie and gets the information about it (rating, wallpaper, poster, description, title, original title, cast, plot, director, writer, release year). Using the plugin it's possible to login to the portal and enter your own rating for selected movie or TV series.

The plugin is prepared based on the resources from the BlackGlass-HD skin (default skin for BlackHole image), so if you want to use it in the other skin you should copy proper resources to the proper location - you should look at skin definition in the sources.



# Installation #

---

  * SSH onto the dreambox
  * install libs: python-html, python-twisted-web, openssl, python-pyopenssl
```
ipkg update
ipkg install python-html
ipkg install python-twisted-web
ipkg install openssl
ipkg install python-pyopenssl
```
  * copy IPK file to /tmp folder
  * use manual IPK package installation option from Dreambox plugin menu

```
ipkg install /tmp/enigma2-plugin-extensions-filmweb_1.0.9_mipsel.ipk
```



# Usage #

---

You could run plugin from two places:
  * from Extension Manager - automatically searches the currently watched movie
  * using INFO button for a long time and than when the list of entries is showed selecting the movie position

I've assigned function registered in the Extension Manager on the YELLOW key button using Multiquick plugin, so when I press the YELLOW button I get the information about currently watched event.

# KEYS DESCRIPTION #
| KEY | Function |
|:----|:---------|
| RED | Exit from plugin |
| GREEN | Show the list of movies to select right one - ambigous search results |
| YELLOW | Show the basic data of movie - switch between TVserie and Movie modes |
| BLUE | Show the descriptions for the current movie |
| EPG | The same as YELLOW |
| MENU | Show the context menu for the plugin |
| MOVIE | Show the Movie Guide window |
| 0   | Show the full actors list - only for Filmweb |
| >   | Switch between Filmweb and IMDB search engine |