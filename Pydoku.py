# TIE-02100 Johdatus ohjelmointiin
# Timo Hartikainen, timo.hartikainen@student.tut.fi
# Tehtävän 13.10 ratkaisu:
# Sudoku graafisella käyttöliittymällä

"""
Sudoku-peli

Käyttöliittymä:
-Liikkuminen nuolinäppäimillä tai hiirellä klikkaamalla
-Numeroiden syöttö numeronäppäimillä (0-9)
--Uusi numero korvaa vanhan
--Numeron poistaminen backspacella
-Pikanäppäimet valikon toiminnoille lukevat toimintojen perässä

Pelin kulku:
-Pelikenttä on tallennettu csv-tiedostoon, joka avataan pelin alussa
-Numeroita syötetään sudokun sääntojen mukaan
--Vain yksi sama numero/rivillä ja 3x3-ruudukossa
-Peli päättyy, kun kaikki numerot on täytetty oikein sääntöjen mukaan
"""

from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
import csv
import os
import threading
import time
import random


class Sudoku:
    def __init__(self):
        # Alustetaan Tkinter-ikkuna
        self.__window = Tk()
        self.__window.title("Pydoku")

        # Alustetaan pelin muuttujat
        self.__sudoku_font = 30
        self.__active_cell = None
        self.__sudoku_paused = False
        self.__clock_running = True
        self.__time_min, self.__time_sec = 0, 0
        self.__clock_thread = None

        # Kysytään pelikentän lähdetiedostoa
        sudoku_filetype = [('Sudoku (.csv)', '.csv')]
        input_file = filedialog.askopenfilename(parent=self.__window,
                                                initialdir=os.getcwd(),
                                                title="Valitse tiedosto:",
                                                filetypes=sudoku_filetype)

        # Lopetetaan suoritus, jos tiedostoa ei valita
        if not input_file:
            self.__window.destroy()
            return

        # Luetaan lähdetiedosto
        file = open(input_file, "r")
        reader = csv.reader(filter(lambda r: not r.startswith("#")
                            and r.rstrip(), file), delimiter=";")

        # Tähän listaan tallennetaan pelikentän numerot csv-tiedostosta
        # Näytettävien numeroiden perässä on tähti (*)
        self.__sudokuNumbers = list()
        for row in reader:
            self.__sudokuNumbers.append(row)
        file.close()

        # Tällä hetkellä 9x9-sudokut tuettu
        self.__dim = len(self.__sudokuNumbers)

        # Tähän listaan tallennetaan numeroiden syötekentät
        self.__sudokuInputs = [[] for i in range(self.__dim)]

        # Alustetaan numeroiden syötekentät
        for i in range(self.__dim):
            for j in range(self.__dim):
                l = Label(self.__window, width=2, height=1,
                          borderwidth=1, relief="ridge")
                l.grid(row=i, column=j)
                l.configure(justify=CENTER, background="white",
                            font=("Arial", self.__sudoku_font, "normal"))

                # Jaotellaan 9x9-ruudukko 3x3-ruutuihin
                if self.dark_cell(i, j):
                    l.configure(background="#DCDCDC")

                if not self.cell_mutable(i, j):
                    # Täytetään näytettävät numerot, joiden perässä tähti (*)
                    l.configure(text=self.__sudokuNumbers[i][j].
                                replace("*", ""),
                                font=("Arial", self.__sudoku_font, 
                                      "underline"))
                else:
                    # Märitetään klikkausfunktio
                    l.bind("<Button-1>", self.cell_on_click_wrapper(i, j))

                self.__sudokuInputs[i].append(l)

        # Alustetaan ikkunan ylävalikko
        menuBar = Menu(self.__window)
        menuBar.add_command(label="Uusi peli (U)", command=self.new_sudoku)
        menuBar.add_command(label="Nollaa (N)", command=self.reset_sudoku)
        menuBar.add_command(label="Tauko (T)",
                            command=self.sudoku_toggle_pause_wrapper())

        # Fontti-valikko
        fontMenu = Menu(menuBar, tearoff=0)
        fontMenu.add_command(label="10",
                             command=self.sudoku_update_font_wrapper(10))
        fontMenu.add_command(label="20",
                             command=self.sudoku_update_font_wrapper(20))
        fontMenu.add_command(label="30",
                             command=self.sudoku_update_font_wrapper(30))
        fontMenu.add_command(label="40",
                             command=self.sudoku_update_font_wrapper(40))
        fontMenu.add_command(label="50",
                             command=self.sudoku_update_font_wrapper(50))
        menuBar.add_cascade(label="Fontti (+/-)", menu=fontMenu)

        # Lisää-valikko
        self.__show_clock = BooleanVar(self.__window)
        self.__highlight_rows = BooleanVar(self.__window)
        self.__show_clock.set(True)
        self.__highlight_rows.set(True)

        moreMenu = Menu(menuBar, tearoff=0)
        moreMenu.add_command(label="Vihje",
                             command=self.sudoku_hint)
        moreMenu.add_command(label="Poista väärät",
                             command=self.remove_incorrect)
        moreMenu.add_checkbutton(label="Naytä aika",
                                 variable=self.__show_clock,
                                 command=self.update_clock_label)
        moreMenu.add_checkbutton(label="Korosta aktiiviset rivit",
                                 variable=self.__highlight_rows,
                                 command=self.toggle_highlighting)
        menuBar.add_cascade(label="Lisää", menu=moreMenu)

        # Lisätään ylävalikko ikkunaan
        self.__window.config(menu=menuBar)
        self.__menu_bar = menuBar

        # Alustetaan ajan näyttö
        self.__clockLabel = Label(self.__window, text="Aika: 00:00")
        self.__clockLabel.grid(row=9, column=0, columnspan=9, ipady=5)

        # Märitetään näppäinfunktio
        self.__window.bind("<Key>", self.window_on_key)

        # Märitetään poistumisfunktio
        self.__window.protocol("WM_DELETE_WINDOW", self.exit_sudoku)

        # Ikkunaan kohdistus on välttämätön pikanäppäinten toiminnalle
        self.__window.focus_force()

        # Käynnistetään ajanotto
        self.start_clock()

    def sudoku_toggle_pause_wrapper(self):
        """
        Palauttaa tauko-funktion referenssin
        :return: function, sudoku_toggle_pause
        """
        def sudoku_toggle_pause():
            """
            Aloittaa ja lopettaa sudokun tauon
            :return: None
            """
            menu = self.__menu_bar
            if not self.sudoku_solved():
                if not self.__sudoku_paused:
                    self.__sudoku_paused = True

                    # Päivitetään Tauko-nappi
                    menu.entryconfigure(3, label="Jatka (T)")

                    # Pysäytetään kello
                    self.__clock_running = False

                    # Poistetaan sudokun pelikenttä näkyvistä
                    self.cell_clear_selection()
                    for i in range(self.__dim):
                        for j in range(self.__dim):
                            l = self.__sudokuInputs[i][j]

                            # Muutetaan ruutujen fontti taustan väriseksi
                            if self.dark_cell(i, j):
                                l.configure(foreground="#DCDCDC")
                            else:
                                l.configure(foreground="white")
                else:
                    self.__sudoku_paused = False

                    # Päivitetään Tauko-nappi
                    menu.entryconfigure(3, label="Tauko (T)")

                    # Muutetaan ruutujen fontti takaisin mustaksi
                    for i in range(self.__dim):
                        for j in range(self.__dim):
                            self.__sudokuInputs[i][j].configure(
                                foreground="black")

                    # Korostetaan valittu ruutu
                    if self.__active_cell is not None:
                        i, j = self.__active_cell
                        self.cell_on_click_wrapper(i, j)()

                    # Käynnistetään kello
                    self.start_clock(True)

        return sudoku_toggle_pause

    def sudoku_update_font_wrapper(self, s: int):
        """
        Palauttaa pelikentän fontin koon päivittävän funktion referenssin
        :param s: int, fontin koko
        :return: function, sudoku_update_font
        """
        def sudoku_update_font():
            """
            Päivittää pelikentän fontin koon
            :return: None
            """
            self.__sudoku_font = s
            for i in range(self.__dim):
                for j in range(self.__dim):
                    l = self.__sudokuInputs[i][j]
                    if self.cell_mutable(i, j):
                        l.configure(font=("Arial", s, "normal"))
                    else:
                        l.configure(font=("Arial", s, "underline"))

        return sudoku_update_font

    def cell_on_click_wrapper(self, i: int, j: int):
        """
        Palauttaa ruudun aktiiviseksi asettavan funktion referenssin
        :param i: int, y-koordinaatti
        :param j: int, x-koordinaatti
        :return: funktio, cell_on_click
        """
        def cell_on_click(event=None):
            """
            Asettaa ruudun aktiiviseksi
            :param event: klikkaustapahtuma
            :return: None
            """
            if not (self.sudoku_solved() or self.__sudoku_paused):
                # Pyyhitään ruutujen korostukset
                self.cell_clear_selection()

                # Korostetaan aktiiviset rivit
                if self.__highlight_rows.get():
                    for n in range(self.__dim):
                        l = self.__sudokuInputs[n][j]
                        l.configure(background="pale green")
                        l = self.__sudokuInputs[i][n]
                        l.configure(background="pale green")

                # Korostetaan aktiivinen ruutu
                l = self.__sudokuInputs[i][j]
                l.configure(background="spring green")

                # Tallennetaan aktiivinen ruutu
                self.__active_cell = (i, j)

        return cell_on_click

    def cell_mutable(self, i: int, j: int):
        """
        Tarkistaa, voiko ruudun  numeroa muuttaa
        :param i: int, y-koordinaatti
        :param j: int, x-koordanaatti
        :return: bool, kyllä/ei
        """
        if 0 <= i < self.__dim and 0 <= j < self.__dim:
            if "*" not in self.__sudokuNumbers[i][j]:
                return True
        return False

    def cell_clear_selection(self):
        """
        Pyyhkii aktiivisten ruutujen korostuksen
        :return: None
        """
        for i in range(self.__dim):
            for j in range(self.__dim):
                l = self.__sudokuInputs[i][j]
                if self.dark_cell(i, j):
                    l.configure(background="#DCDCDC")
                else:
                    l.configure(background="white")

    def window_on_key(self, event):
        """
        Syöttää (poistaa) numeron aktiivisen ruutuun ja
        käsittelee pikanäppäintoiminnot
        :param event: näppäintapahtuma
        :return: None
        """
        if self.__active_cell is not None and \
                ((event.char and event.char in "123456789")
                 or event.keycode == 8):
            # Käsitellään numerosyötteet
            i, j = self.__active_cell
            l = self.__sudokuInputs[i][j]

            # Tyhjennetään ruutu aina, kun syötetään uusi numero
            # tai Backspace (event.keycode == 8)
            l.configure(text="")

            # Syötetään uusi numero
            if event.char in "123456789":
                l.configure(text=event.char)

            # Tarkistetaan sudokun ratkaisu
            if self.sudoku_solved():
                self.mark_solved()
        else:
            # Käsitellään nuolinäppäimet
            if self.__active_cell is not None:
                c = event.keycode
                i, j = self.__active_cell
                delta_i, delta_j = 0, 0
                if c == 37:  # vasen
                    delta_j = -1
                elif c == 38:  # ylös
                    delta_i = -1
                elif c == 39:  # oikea
                    delta_j = 1
                elif c == 40:  # alas
                    delta_i = 1

                # Tarkistetaan nuolinäppäinten painallukset ja valitaan ruutu
                if delta_i != delta_j:
                    for n in range(1, self.__dim):
                        if self.cell_mutable(i + delta_i * n, j + delta_j * n):
                            self.cell_on_click_wrapper(i + delta_i * n,
                                                       j + delta_j * n)()
                            break

            # Käsitellään pikanäppäintoiminnot
            k = event.char.upper()
            f = self.__sudoku_font
            if k == "U":
                self.new_sudoku()
            elif k == "N":
                self.reset_sudoku()
            elif k == "T":
                self.sudoku_toggle_pause_wrapper()()
            elif k == "+":
                if f < 50:
                    self.sudoku_update_font_wrapper(f + 10)()
            elif k == "-":
                if f > 10:
                    self.sudoku_update_font_wrapper(f - 10)()

    def start_clock(self, resume=False):
        """
        Käynnistää kellon
        :return: None
        """
        self.__clock_running = True

        # Nollataan aika, jos kello käynnistetään alusta
        if not resume:
            self.__time_min, self.__time_sec = 0, 0

        self.__clock_thread = threading.Thread(target=self.update_clock)
        self.__clock_thread.start()

    def update_clock(self):
        """
        Päivittää kellon lukemaa
        :return: None
        """
        time.sleep(1)
        while self.__clock_running:
            self.__time_sec += 1
            if self.__time_sec == 60:
                self.__time_min += 1
                self.__time_sec = 0

            # Päivitetään kellotaulu
            self.update_clock_label()

            time.sleep(1)

    def update_clock_label(self):
        """
        Päivittää kellotaulun
        :return: None
        """
        if self.__show_clock.get():
            # Kello käytössä
            self.__clockLabel. \
                configure(text="Aika: {}:{}".format(
                self.__time_min if len(str(self.__time_min)) > 1
                else "0" + str(self.__time_min),
                self.__time_sec if len(str(self.__time_sec)) > 1
                else "0" + str(self.__time_sec)))
        else:
            # Kello piilotettu
            self.__clockLabel.configure(text="Aika: --:--")

        # Muutetaan kellon fontin väriä, jos sudoku ratkaistu
        self.__clockLabel.configure(
            foreground="green" if self.sudoku_solved()
                                  and not self.__clock_running
                                  and self.__show_clock.get() else "black")

    def dark_cell(self, i: int, j: int):
        """
        Tarkistaa, onko kyseessä tumma ruutu
        :param i: int, y-koordinaatti
        :param j: int, x-koordinaatti
        :return: bool, kyllä/ei
        """
        if (i in [0, 1, 2, 6, 7, 8] and j in [3, 4, 5]) or \
                (i in [3, 4, 5] and j in [0, 1, 2, 6, 7, 8]):
            return True
        return False

    def sudoku_solved(self):
        """
        Tarkistaa, onko sudoku ratkaistu
        :return: bool, kyllä/ei
        """
        for i in range(self.__dim):
            for j in range(self.__dim):
                if not self.__sudokuInputs[i][j].cget("text") == \
                       self.__sudokuNumbers[i][j].replace("*", ""):
                    return False
        return True

    def mark_solved(self):
        """
        Merkitsee sudokun ratkaistuksi
        :return: None
        """
        # Pysäytettään kello
        self.__clock_running = False
        self.update_clock_label()

        # Poistetaan aktiivinen ruutu ja korostukset
        self.__active_cell = None
        self.cell_clear_selection()

        # Muutetaan ruutujen fontin väri
        for i in range(self.__dim):
            for j in range(self.__dim):
                self.__sudokuInputs[i][j].configure(foreground="green")

    def new_sudoku(self):
        """
        Aloittaa uuden sudokun
        :return: None
        """
        # Varmistetaan uuden sudokun aloitus
        if messagebox.askokcancel("Uusi peli",
                                  "Haluatko varmasti aloittaa uuden pelin?"):
            # Pysäytetään kello
            self.__clock_running = False

            # Suljetaan ikkuna
            self.__window.destroy()

            # Aloitetaan uusi sudoku
            main()

    def reset_sudoku(self):
        """
        Nollaa syötteet ja kellon
        :return: None
        """
        # Varmistetaan nollaus
        if messagebox.askokcancel("Nollaa",
                                  "Haluatko varmasti nollata ratkaisun?"):
            # Pyyhitään korostukset
            self.cell_clear_selection()

            for i in range(self.__dim):
                for j in range(self.__dim):
                    l = self.__sudokuInputs[i][j]

                    # Muutetaan ruutuen fontti mustaksi
                    # ja tyhjennetään kaikki ruudut
                    l.configure(foreground="black", text="")

                    # Lisätään näytettävät numerot ruutuihin
                    if "*" in self.__sudokuNumbers[i][j]:
                        l.configure(text=self.__sudokuNumbers[i][j].
                                    replace("*", ""))

            # Poistetaan aktiivinen ruutu
            self.__active_cell = None

            # Poistetaan tauko
            self.__sudoku_paused = False
            self.__menu_bar.entryconfigure(3, label="Tauko (T)")

            # Nollataan ka käynnistetään kello
            self.__time_min, self.__time_sec = 0, 0
            self.update_clock_label()
            if not self.__clock_running:
                self.start_clock()

    def sudoku_hint(self):
        """
        Täyttää yhden puuttuvan numeron
        :return: None
        """
        if not (self.sudoku_solved() or self.__sudoku_paused):
            while True:
                # Valitaan satunnainen ruutu
                i = random.randint(0, self.__dim - 1)
                j = random.randint(0, self.__dim - 1)

                # Päivitetään oikea vastaus ruutuun, joka ei ole vielä oikein
                l = self.__sudokuInputs[i][j]
                ans = self.__sudokuNumbers[i][j].replace("*", "")
                if not l.cget("text") == ans:
                    l.configure(text=ans)

                    # Tarkistetaan sudokun ratkaisu
                    if self.sudoku_solved():
                        self.mark_solved()

                    break

    def remove_incorrect(self):
        """
        Poistaa väärät numerot ruuduista
        :return: None
        """
        if not (self.sudoku_solved() or self.__sudoku_paused):
            for i in range(self.__dim):
                for j in range(self.__dim):
                    l = self.__sudokuInputs[i][j]

                    # Näytettävien numeroiden perässä tähti (*)
                    ans = self.__sudokuNumbers[i][j].replace("*", "")

                    if not l.cget("text") == ans:
                        l.configure(text="")

    def toggle_highlighting(self):
        """
        Näyttää ja piilotaa ruutujen korostuksen
        :return:
        """
        if self.__active_cell is not None:
            i, j = self.__active_cell
            self.cell_on_click_wrapper(i, j)()

    def exit_sudoku(self):
        """
        Lopettaa sudokun
        :return: None
        """
        # Varmistetaan poistuminen
        if messagebox.askokcancel("Poistu", "Haluatko varmasti poistua?"):
            # Pysäytetään kello
            self.__clock_running = False
            self.__clock_thread.join()

            self.__window.destroy()

    def start(self):
        """
        Käynnistää graafisen käyttöliittymän
        :return: None
        """
        self.__window.mainloop()


def main():
    ui = Sudoku()
    ui.start()


main()
