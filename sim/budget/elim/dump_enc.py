from macro import templates
with open('enc.txt','w') as f:
    for name,g,tab in templates():
        m=[sum(b<<j for j,b in enumerate(t)) for t in tab]
        f.write(f"{name.replace(' ','_')} {g} {m[0]} {m[1]}\n")
print(len(templates()))
