#!/usr/bin/python3
#!/usr/bin/env python

from cmath import polar
import numpy as np                  # seems available on python3, if not $> pip3 install numpy
import matplotlib.pyplot as plt     #> pip3 install matplotlib ; pip3 install tk
import sys
from os.path import exists

DEGREE = 5
DEBUG = True

X = Y = None 

power_tab = []

def dichotomic_search(value):
    # search nearest value in array using DICHOTOMIC METHOD
    # and interpolate return value
    global power_tab
    x = int(value)
    n = len(power_tab)
    lo = 0
    hi = n - 1
    mid = 0
    if x < 0: return 0
    while lo <= hi:
        mid = (hi + lo) // 2
        if power_tab[mid] < x:
            lo = mid + 1
            adj = 1
        elif power_tab[mid] > x:
            hi = mid - 1
            adj = 0
        else:
            break
    i = mid + adj
    print("Adj = " + str(adj)) if DEBUG else ''

    if (i >= n): return 100

    dist = power_tab[i] - power_tab[i-1]
    print(dist)  if DEBUG else ''
    r = 0.5 / (dist / (int(value) - power_tab[i-1] ))
    print(r)  if DEBUG else ''
    print(str(power_tab[i]) + " - " + str(power_tab[i-1])) if DEBUG else ''
    print(str(i/2) + " - " + str((i-1)/2)) if DEBUG else ''
    print("i = " + str(i))
    return (((i-1)/2+r))

def power_to_percent(value):
    # search nearest value in array using BRUT SEARCH method
    # and interpolate return value
    global power_tab
    if int(value) < 0: return 0
    for i in range(200):
        if (int(value) < power_tab[i]): break
    else:
        print("not found")    
    if (power_tab[200] < int(value)): return 100
    else:
        dist = power_tab[i] - power_tab[i-1]
        print(dist)  if DEBUG else ''
        r = 0.5 / (dist / (int(value) - power_tab[i-1] ))
        print(r)  if DEBUG else ''
        print(str(power_tab[i]) + " - " + str(power_tab[i-1])) if DEBUG else ''
        print(str(i/2) + " - " + str((i-1)/2)) if DEBUG else ''
        print("i = " + str(i))
        return (((i-1)/2+r))



def readCSV(csv_file):
    global X, Y
    print("reading CSV " + csv_file)
    with open(csv_file) as file_name:
        array = np.loadtxt(file_name, delimiter=";")
    X = list(tuple(x[0] for x in array))
    Y = list(tuple(x[1] for x in array))
    
def main():
    calibrationFile = sys.argv[1]
    try:
        print ("opening csv : " + calibrationFile)
        readCSV(calibrationFile)
    except FileNotFoundError as fnf_error:
        print(fnf_error)
        exit()
    except:
        print (calibrationFile + " bad format, delimiter...")
        exit()

    #  Algorithm (Polynomial) https://numpy.org/doc/stable/reference/generated/numpy.polyfit.html
    poly_fit = np.polyfit(X,Y, DEGREE)
    
    mypoly = np.poly1d(poly_fit)

    # New predict.
    print("\nPolynomial function :")
    print("\n", mypoly )
    print("\nCoef/Vector :") 
    print( mypoly.c)
    print("")

    outfile = sys.argv[1] 
    outfile = outfile.replace(".", "_poly.")

    csv_file = open(outfile, "w") 

    for percent in np.arange(100, -0.5, -0.5):
        P = (mypoly(percent))
        print("Calculate x = " + str(percent)+ " -> P = ", P) # evaluate at x='percent'
        line = '{};{}\n'.format(percent, P)
        line = line.replace(".", ",")
        sys.stdout.flush()  
        csv_file.write(line)
        power_tab.append(P)

    power_tab.reverse()
    print (power_tab)
    print ("p[0]   : " + str(power_tab[0]))
    print ("p[1]   : " + str(power_tab[1]))
    print ("p[199] : " + str(power_tab[199]))
    print ("p[200] : " + str(power_tab[200]))
    
    csv_file.close()   
    print(" saved into -> ", outfile)

    # Plot data
    xx = np.linspace(0, 100)
    plt.plot(xx, mypoly(xx), c='r',linestyle='-')
    plt.title('Polynomial curve')
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.grid(True)
    plt.scatter(X, Y)

    print("\nEnter Power or '999' to quit, '888' to plot")
    x = ""
    while (x != "999" and x != "888"): 
        print("")
        x = input("Power : ")
        print("\n*** BRUT SEARCH")
        percent = power_to_percent(x)
        print("           p(" + x + ")=" + str(percent)+ " %" )
        print("\n*** DICHOTOMIC SEARCH")
        percent = dichotomic_search(x)
        print("           p(" + x + ")=" + str(percent)+ " %" )
        print("\n*** POLY")
        P = (mypoly(percent))
        print("           p(" + str(percent) + ")% = " + str(P)+ " W" )
        

    if x == "999":
        print("Bye")
    if x =="888":
        plt.show()

if __name__ == "__main__":
    main()