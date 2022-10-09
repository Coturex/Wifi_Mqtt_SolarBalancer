#!/usr/bin/python3
#!/usr/bin/env python

import numpy as np                  # seems available on python3, if not $> pip3 install numpy
import matplotlib.pyplot as plt     #> pip3 install matplotlib ; pip3 install tk
import sys
from os.path import exists

#X = [1, 5, 8, 10, 14, 18]
#Y = [1, 1, 10, 20, 45, 75]

X = Y = None 

def readCSV(csv_file):
    global X, Y
    with open(csv_file) as file_name:
        array = np.loadtxt(file_name, delimiter=";")
    # print(array)
    X = list(tuple(x[0] for x in array))
    Y = list(tuple(x[1] for x in array))
    
    
def main():
    try:
        if exists(sys.argv[1]):
            readCSV(sys.argv[1])
        print ("opening csv : " + sys.argv[1])
    except:
        print ("opening csv : power_calibration.csv")
        readCSV("power_calibration.csv")
    
    #  Algorithm (Polynomial) https://numpy.org/doc/stable/reference/generated/numpy.polyfit.html
    degree = 5
    poly_fit = np.poly1d(np.polyfit(X,Y, degree))

    # New predict.
    print("\nPolynomial function :")
    print("\n", poly_fit )
    print("\nCoef/Vector :") 
    print( poly_fit.c)
    print("")

    outfile = sys.argv[1] 
    outfile = outfile.replace(".", "_poly.")

    csv_file = open(outfile, "w") 
    for percent in np.arange(100, -0.5, -0.5):
        P = (poly_fit(percent))
        #print("Calculate x = " + str(percent)+ " -> P = ", P) # evaluate at x='percent'
        line = '{};{}\n'.format(percent, P)
        line = line.replace(".", ",")
        sys.stdout.flush()  
        csv_file.write(line)

    csv_file.close()   

    print(" saved into -> ", outfile)

    # Plot data
    xx = np.linspace(0, 100)
    plt.plot(xx, poly_fit(xx), c='r',linestyle='-')
    plt.title('Polynomial curve')
    plt.xlabel('X')
    plt.ylabel('Y')
    #plt.axis([0, 100, 0, 100])
    plt.grid(True)
    plt.scatter(X, Y)
    plt.show()

if __name__ == "__main__":
    main()