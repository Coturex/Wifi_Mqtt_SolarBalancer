#!/usr/bin/python3
import numpy as np  
import matplotlib.pyplot as plt

#X = [1, 5, 8, 10, 14, 18]
#Y = [1, 1, 10, 20, 45, 75]

X = Y = None
def readCSV(csv_file):
    global X, Y
    with open(csv_file) as file_name:
        array = np.loadtxt(file_name, delimiter=",")
    # print(array)
    X = list(tuple(x[0] for x in array))
    Y = list(tuple(x[1] for x in array))
    print(X)
    print(Y)

readCSV("calibration/power_calibration.csv")
print("-----")

#  Algorithm (Polynomial) https://numpy.org/doc/stable/reference/generated/numpy.poly1d.html
degree = 5
poly_fit = np.poly1d(np.polyfit(X,Y, degree))

# New predict.
print( poly_fit )
print ("coefs are :") 
print( poly_fit.c)
print("x = 50 -> P= ", poly_fit(50)) # evaluate at x=50
print("-----")


# Plot data
xx = np.linspace(0, 20, 100)
plt.plot(xx, poly_fit(xx), c='r',linestyle='-')
plt.title('Polynomial')
plt.xlabel('X')
plt.ylabel('Y')
plt.axis([0, 20, 0, 100])
plt.grid(True)
plt.scatter(X, Y)
plt.show()

