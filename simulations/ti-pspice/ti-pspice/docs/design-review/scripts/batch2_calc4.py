import numpy as np
f=517.0; s=2j*np.pi*f
R17=4.64e3;R18=18.7e3;R21=4.64e3;R22=4.64e3;C1=C2=C3=33e-9;C4=130e-9
def chain(CB=0,CM=0,Gina=11.0,wire=0):
    # HP nodes A,B ; follower out Hp=B
    Y=lambda x:x
    A=np.array([[1/R17+s*C1+s*C2, -(1/R17+s*C2)],[-s*C2, s*C2+1/R18+s*CB]])
    b=np.array([s*C1*Gina,0]); Aa,B=np.linalg.solve(A,b)
    Hp=B
    A2=np.array([[1/R22+1/R21+s*C4, -(1/R21+s*C4)],[-1/R21, 1/R21+s*C3+s*CM]])
    b2=np.array([Hp/R22,0]); N,M=np.linalg.solve(A2,b2)
    return M
M0=chain(); print(abs(M0),np.degrees(np.angle(M0)))
for CB,CM in [(8e-12,8e-12),(6.4e-12,6.4e-12),(8e-12,0),(0,8e-12),(15e-12,15e-12)]:
    M=chain(CB,CM); r=M/M0; print(CB,CM,"gain %",(abs(r)-1)*100,"phase deg",np.degrees(np.angle(r)))
