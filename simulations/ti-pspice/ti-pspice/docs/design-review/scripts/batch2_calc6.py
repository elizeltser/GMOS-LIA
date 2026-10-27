import numpy as np
f=517.0; s=2j*np.pi*f
R17=4.64e3;R18=18.7e3;R21=4.64e3;R22=4.64e3;C1=C2=C3=33e-9;C4=130e-9
def solve(Z, Vd=15e-3, ref_in=0):
    # unknowns A,B,N,M,Vn ; ground=0 ; Vref source ideal 0 (ac) behind Z
    # Vin_ina = 11*Vd + Vn
    # HP: C1 from Vin to A ; C2 A-B ; R17 A-B(Hp=B) ; R18 B - Vn ; follower Hp=B
    # LP: R22 B-N ; R21 N-M ; C4 N-M(out=M) ; C3 M-Vn
    Y=np.zeros((5,5),complex); b=np.zeros(5,complex)
    iA,iB,iN,iM,iV=range(5)
    # node A
    Y[iA,iA]+=s*C1+1/R17+s*C2; Y[iA,iB]-=1/R17+s*C2; Y[iA,iV]-=s*C1
    b[iA]+=s*C1*11*Vd
    # node B: C2 (B-A), R18 (B-Vn); follower output current does not matter (ideal op amp supplies), but B is op-amp input => no extra current. R17 from A to HPF = B too, 
    # careful: R17 returns to op amp OUTPUT (=B), not to node B as KCL node: B node KCL: s*C2*(B-A)+(B-Vn)/R18 = 0
    Y[iB,iB]+=s*C2+1/R18; Y[iB,iA]-=s*C2; Y[iB,iV]-=1/R18
    # fix node A KCL: R17 goes to output=B voltage -> already coded (A-B)/R17
    # node N: (N-B)/R22 + (N-M)/R21 + s*C4*(N-M)=0
    Y[iN,iN]+=1/R22+1/R21+s*C4; Y[iN,iB]-=1/R22; Y[iN,iM]-=1/R21+s*C4
    # node M (op-amp +): (M-N)/R21 + s*C3*(M-Vn)=0
    Y[iM,iM]+=1/R21+s*C3; Y[iM,iN]-=1/R21; Y[iM,iV]-=s*C3
    # Vref node: Vn/Z = sum of currents into node: (B-Vn)/R18 + s*C3*(M-Vn) + s*C1*0.. (C1 connects to INA output = 11Vd+Vn -> A; not to Vn node directly)
    Y[iV,iV]+=1/Z+1/R18+s*C3; Y[iV,iB]-=1/R18; Y[iV,iM]-=s*C3
    # but C1 is driven by INA out which is a source relative to ground: current drawn from INA output, supplied by its output stage; it's referenced through REF? ignore
    x=np.linalg.solve(Y,b); A,B,N,M,Vn=x
    return (M-Vn)/Vd, Vn
g0,_=solve(1e-6); print("Z~0",abs(g0),np.degrees(np.angle(g0)))
for Z in [0.1,1,10,100,1e3,2.5e3]:
    g,Vn=solve(Z); print(f"Z={Z:7.1f} gain {abs(g):.5f} ({(abs(g)/abs(g0)-1)*100:+.4f} %) phase {np.degrees(np.angle(g)):.4f} deg ({np.degrees(np.angle(g/g0)):+.4f}) |Vn|/Vd {abs(Vn)/15e-3:.5f}")
