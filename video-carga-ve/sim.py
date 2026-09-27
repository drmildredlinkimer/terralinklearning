import numpy as np
DT=5/60; T0=17.0; T1=32.0  # 17:00 -> 08:00 next day
N=int(round((T1-T0)/DT)); t=T0+np.arange(N)*DT
PMAX=7.4; BAT=60.0; TARGET=0.80
# name, arrival h, departure h (+24 next day), SoC
EVS=[("VE1",17.00,30.5,0.30),("VE2",17.75,31.0,0.20),("VE3",18.50,22.0,0.50),
     ("VE4",19.25,29.5,0.40),("VE5",20.00,32.0,0.60)]
need=np.array([(TARGET-s)*BAT for *_ ,s in EVS])
# static priority = laxity at arrival: time until departure minus hours needed at full power.
# Combines departure time and SoC (lower SoC -> more energy needed -> less slack).
LAX=np.array([(d-a)-need[i]/PMAX for i,(n,a,d,s) in enumerate(EVS)])
ORDER=list(np.argsort(LAX))
def uncontrolled():
    P=np.zeros((5,N))
    for i,(n,a,d,s) in enumerate(EVS):
        e=need[i]
        for k in range(N):
            if t[k]>=a-1e-9 and e>1e-9:
                p=min(PMAX,e/DT); P[i,k]=p; e-=p*DT
    return P
def managed(cap):
    P=np.zeros((5,N)); rem=need.copy()
    order=ORDER
    for k in range(N):
        room=cap
        for i in order:
            a,d=EVS[i][1],EVS[i][2]
            if a-1e-9<=t[k]<d and rem[i]>1e-9 and room>0:
                p=min(PMAX,rem[i]/DT,room); P[i,k]=p; rem[i]-=p*DT; room-=p
    return P,rem
lo,hi=1,40
for _ in range(40):
    m=(lo+hi)/2; _,r=managed(m)
    (hi,lo)=(m,lo) if r.max()<1e-6 else (hi,m)
CAP=hi
if __name__=="__main__":
    U=uncontrolled(); M,r=managed(CAP)
    print("need",need,need.sum()); print("lax",LAX.round(2),"order",ORDER); print("cap",CAP)
    print("peak U",U.sum(0).max(),"at",t[U.sum(0).argmax()]); print("peak M",M.sum(0).max())
    print("E U",U.sum()*DT,"E M",M.sum()*DT)
    for k in range(0,N,6): print(f"{t[k]%24:5.2f} U={U[:,k].sum():5.1f} M={M[:,k].sum():5.1f}", np.round(M[:,k],1))
