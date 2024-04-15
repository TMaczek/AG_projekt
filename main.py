import pandas as pd
import numpy as np
import math
import pygad
from random import randint
import matplotlib.pyplot as plt
from matplotlib.pyplot import cm
from matplotlib.ticker import FuncFormatter



# funkcja zwracajaca wage dostepnosci, uzywana przy obrobce danych z dataframe na tablice pythona
def dostepnosc(row):
    t = row[3]
    if t == 'TAK':
        return 1.0
    return 0.5


# liczenie ilosci zmian w rozkladzie (parametr g w opisie projektu)
def changes(arr):
    chg = 0
    for i in range(1, len(arr)):
        if arr[i] != arr[i - 1]:
            chg += 1
    return chg


# tworzenie wlasnej populacji startowej, w ktorej przydzialy sa losowe, ale mozliwe do przydzielenia
def custom_population(dostepnosci, size):
    pop = []

    for i in range(1, len(dostepnosci)):
        pop.append([math.ceil(x) * i for x in dostepnosci[i]])
    # shuffle
    new_pop = []
    for i in range(size):
        new_one = []
        for j in range(len(pop[0])):
            x = randint(0, len(pop) - 1)
            new_one.append(pop[x][j])
        new_pop.append(new_one)

    return new_pop


# funkcja dopasowania (nieuzyte argumenty by zachowac konwencje pygad)
def fitness_func(ga_instance, solution, solution_idx):
    f = 0
    g = 0
    for i in range(len(solution)):
        v = int(solution[i])
        if dostepnosci[v][i] == 0:
            solution[i] = 0  # fixing (in case of a bad mutation)
            # f -= 1
        else:
            f += dostepnosci[v][i]
    g = changes(solution)
    return [f, 144 - g]


# funkcja pomocnicza przeliczajaca ilosc minut od 00:00 na zapis godzinowy (np. 500 -> 8:20)
def min2hour(x, pos=0):
  hours = int(x / 60)
  minutes = int(x % 60)
  return f'{hours:02d}:{minutes:02d}'


if __name__ == "__main__":
    # set up przed petla dla kazdego dnia tygodnia
    df = pd.read_csv(r"dostepnosc.txt", sep=" ", header=None)
    dni_tygodnia = ['pn', 'wt', 'sr', 'cz', 'pt', 'sb', 'nd']
    fullnames = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
    file = open("output.txt", "w")
    dostepnosci = []

    # petla iterujaca po dniach tygodnia
    for day, fullname in zip(dni_tygodnia, fullnames):
        # selekcja rekordow tylko z danego dnia
        day_df = df[df[1] == day]
        # obrobka danych z pliku
        day_df[0].unique()
        #tablice pomocnicze do przetwarzania danych z pliku
        # values - bedzie przechowywac index osoby
        values = []
        # starty - bedzie przechowywac numer kolejnej 10 minutowki w dniu (poczatek zmiany osoby)
        starty = []
        # konce - bedzie przechowywac numer 10 minutowki gdzie osoba konczy
        konce = []

        for index, row in day_df.iterrows():
            values.append(np.where(day_df[0].unique() == row[0])[0][0] + 1)
            godziny = day_df[2][index].split('-')
            begin = godziny[0].split(':')
            start = 6 * int(begin[0]) + int(begin[1][0])

            finish = godziny[1].split(':')
            end = 6 * int(finish[0]) + int(finish[1][0])

            starty.append(start)
            konce.append(end)

        # tutaj do dataframe dopisane sa kolejne wartosci z trzech opisanych wczesniej tablic
        day_df = day_df.assign(person_index=values, start=starty, koniec=konce)
        day_df['dostepnosc'] = day_df.apply(dostepnosc, axis=1)

        # gene_space - jeden z parametrow AG w pygad, są to unikalne indeksy osob oraz 0 dla braku osoby
        gene_space = range(0, len(day_df[0].unique()) + 1)
        osoby = day_df[0].unique()
        # sprawdzenie czy na dany dzien tygodnia sa wogole chetni - jesli nie, omijamy wykonanie algorytmu
        if len(osoby) < 1:
            continue # brak ludzi na dany dzien

        dostepnosci = [[0 for x in range(24 * 6)] for y in gene_space]

        # uzupelnienie tablic dostepnosci
        for index, row in day_df.iterrows():
            i = row['person_index']
            start = row['start']
            koniec = row['koniec']
            dst = row['dostepnosc']

            for j in range(start, koniec):
                dostepnosci[i][j] = dst

        # parametry algorytmu
        num_generations = 150
        num_parents_mating = 8
        fitness_function = fitness_func
        initial_population = custom_population(dostepnosci, 80) # tutaj ilosc zamiast sol_per_pop
        parent_selection_type = "nsga2"
        crossover_type = "uniform"
        crossover_probability = 0.8
        mutation_type = "random"
        mutation_num_genes = 10
        gene_type = int

        # algorytm
        ga_instance = pygad.GA(num_generations=num_generations,
                               num_parents_mating=num_parents_mating,
                               fitness_func=fitness_function,
                               initial_population= initial_population,
                               gene_space=gene_space,
                               parent_selection_type=parent_selection_type,
                               crossover_type=crossover_type,
                               crossover_probability=crossover_probability,
                               mutation_type=mutation_type,
                               mutation_num_genes=mutation_num_genes,
                               gene_type=gene_type)

        ga_instance.run()

        solution, solution_fitness, solution_idx = ga_instance.best_solution(ga_instance.last_generation_fitness)

        # tworzenie pliku oraz wykresow dostepnosci
        begin = []
        end = []
        person = []
        color = cm.rainbow(np.linspace(0, 1, len(osoby)))
        colors = []

        minutes = 0
        last_one = 0
        for v in solution:
            if v == 0:
                if last_one != 0:
                    file.write(f'{min2hour(minutes)}\n')
                    end.append(minutes)
                    last_one = 0
            else:
                if last_one == 0:
                    last_one = v
                    file.write(f'{osoby[last_one - 1]} {day} {min2hour(minutes)}-')
                    begin.append(minutes)
                    person.append(osoby[last_one - 1])
                    colors.append(color[last_one - 1])
                if last_one != v:
                    file.write(f'{min2hour(minutes)}\n')
                    end.append(minutes)
                    last_one = v
                    file.write(f'{osoby[last_one - 1]} {day} {min2hour(minutes)}-')
                    begin.append(minutes)
                    person.append(osoby[last_one - 1])
                    colors.append(color[last_one - 1])
            minutes += 10


        # plotowanie wykresow
        begin = np.array(begin)
        end = np.array(end)
        plt.figure()
        plt.grid()
        plt.barh(range(len(begin)), end - begin, left=begin, color=colors)

        plt.yticks(range(len(begin)), person)
        plt.gca().xaxis.set_major_formatter(FuncFormatter(min2hour))
        plt.title(f'Grafik na {fullname}')
        plt.savefig(f'grafik_{day}.png')

    file.close()
