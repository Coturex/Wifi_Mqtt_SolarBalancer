#!/usr/bin/python
import numpy as np
#import matplotlib.pyplot as plt

X = [1, 5, 8, 10, 14, 18]
Y = [1, 1, 10, 20, 45, 75]

def readCSV(csv_file):
    with open(csv_file) as file_name:
        array = np.loadtxt(file_name, delimiter=",")
    # print(array)
    X = list(tuple(x[0] for x in array))
    Y = list(tuple(x[1] for x in array))
    print(X)
    print(Y)


readCSV("calibration/power_calibration.csv")
print("-----")

# Train Algorithm (Polynomial)
degree = 5
poly_fit = np.poly1d(np.polyfit(X,Y, degree))

# New predict.
print( poly_fit )
print ("coefs are :") 
print( poly_fit.c)
print("-----")


# Plot data
# xx = np.linspace(0, 26, 100)
# plt.plot(xx, poly_fit(xx), c='r',linestyle='-')
# plt.title('Polynomial')
# plt.xlabel('X')
# plt.ylabel('Y')
# plt.axis([0, 25, 0, 100])
# plt.grid(True)
# plt.scatter(X, Y)
# plt.show()


