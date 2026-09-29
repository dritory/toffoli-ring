// gate-word BFS: gsearch GATE g t0 t1 rest pad maxdepth maxstates mode letter...
// GATE: NOT RESET CNOT:c:t TOFF:a:b:t CMOV+ CMOV-  ; letter e.g. F,T0,P+K  (comma separated ops, optional +K)
#include <bits/stdc++.h>
using namespace std;
struct Bd{ vector<char> ops; bool mark; };
static bool runb(const Bd& b,int mode,int&tape,int&ptr,int&S,int W){
  if(S){ if(!b.mark) return true; if(mode==0){S=0;return true;} }
  int S2=0;
  for(char op:b.ops){
    if(op=='F') tape^=1<<ptr;
    else if(op=='0'||op=='1'){ if(((tape>>ptr)&1)==(op-'0')) S2=1; }
    else { ptr+=(op=='P')?1:-1; if(ptr<0||ptr>=W) return false; }
  }
  S=S2; return true;
}
Bd parse(string s){ Bd b; b.mark=false; if(s.size()>=2&&s.substr(s.size()-2)=="+K"){b.mark=true;s=s.substr(0,s.size()-2);} 
  stringstream ss(s); string t; while(getline(ss,t,',')){ if(t.empty())continue; if(t=="F")b.ops.push_back('F'); else if(t=="T0")b.ops.push_back('0'); else if(t=="T1")b.ops.push_back('1'); else if(t=="P")b.ops.push_back('P'); else if(t=="M")b.ops.push_back('M'); } return b; }
int main(int argc,char**argv){
  string gate=argv[1]; int g=atoi(argv[2]); int tab[2]={atoi(argv[3]),atoi(argv[4])}; int rest=atoi(argv[5]); int pad=atoi(argv[6]);
  int maxd=atoi(argv[7]); long maxs=atol(argv[8]); int mode=atoi(argv[9]);
  vector<Bd> L; for(int i=10;i<argc;i++) L.push_back(parse(argv[i]));
  // gate spec: offsets
  vector<int> offs{0}; int kind=0; int ca=0,cb=0,ct=0;
  if(gate=="NOT") kind=1; else if(gate=="RESET") kind=2; else if(gate=="CMOV+") kind=5; else if(gate=="CMOV-") kind=6; else if(gate=="CMOVK+") kind=7; else if(gate=="CMOVK-") kind=8; else if(gate=="BACKL"){ kind=9; offs.push_back(-1);} else if(gate=="BACKR"){ kind=10; offs.push_back(1);}
  else if(gate.rfind("CNOT",0)==0){ kind=3; sscanf(gate.c_str(),"CNOT:%d:%d",&ca,&ct); offs.push_back(ca); offs.push_back(ct);} 
  else if(gate.rfind("TOFF",0)==0){ kind=4; sscanf(gate.c_str(),"TOFF:%d:%d:%d",&ca,&cb,&ct); offs.push_back(ca); offs.push_back(cb); offs.push_back(ct);} 
  int lo=*min_element(offs.begin(),offs.end())-pad, hi=*max_element(offs.begin(),offs.end())+pad;
  if(kind==6||kind==8||kind==9) lo=min(lo,-1-pad); if(kind==5||kind==7||kind==10) hi=max(hi,1+pad);
  int ng=hi-lo+1, W=ng*g, base=-lo*g+rest; int nc=1<<ng;
  auto pack=[&](int c){int t=0;for(int i=0;i<ng;i++){int x=(c>>i)&1;t|=tab[x]<<(i*g);}return t;};
  vector<uint32_t> init(nc),exp(nc);
  for(int c=0;c<nc;c++){ init[c]=(pack(c)<<8)|(base<<1);
    auto X=[&](int o){return (c>>(o-lo))&1;}; int c2=c, dp=0;
    switch(kind){ case 1: c2^=1<<(0-lo); break; case 2: c2&=~(1<<(0-lo)); break;
      case 3: if(X(ca)) c2^=1<<(ct-lo); break; case 4: if(X(ca)&&X(cb)) c2^=1<<(ct-lo); break;
      case 7: if(X(0)) dp=1; break; case 8: if(X(0)) dp=-1; break; case 9: if(X(-1)) dp=-1; break; case 10: if(X(1)) dp=1; break;
      case 5: if(X(0)){c2&=~(1<<(0-lo)); dp=1;} break; case 6: if(X(0)){c2&=~(1<<(0-lo)); dp=-1;} break; }
    exp[c]=(pack(c2)<<8)|((base+dp*g)<<1); }
  string pre = getenv("PREFIX")? getenv("PREFIX"):"";
  for(char ch: pre){ int li=ch-'0'; for(int c=0;c<nc;c++){ uint32_t v=init[c]; int tape=v>>8,ptr=(v>>1)&127,S=v&1; if(!runb(L[li],mode,tape,ptr,S,W)){ printf("PREFIX OOB\n"); return 0;} init[c]=(tape<<8)|(ptr<<1)|S; } }
  if(init==exp){ printf("EMPTY\n"); return 0; }
  // BFS with parent pointers; store states as vector<uint32_t>[nc] in a big pool
  struct Node{ int parent; char letter; };
  vector<Node> nodes; vector<uint32_t> pool; 
  auto hashv=[&](const uint32_t*v){ uint64_t h=1469598103934665603ULL; for(int i=0;i<nc;i++){ h^=v[i]; h*=1099511628211ULL; h^=h>>29;} return h; };
  unordered_set<uint64_t> seen; 
  pool.insert(pool.end(),init.begin(),init.end()); nodes.push_back({-1,0}); seen.insert(hashv(init.data()));
  size_t fs=0, fe=1; int K=L.size();
  for(int d=1; d<=maxd; d++){
    size_t nfe=nodes.size();
    for(size_t i=fs;i<fe;i++){
      for(int li=0;li<K;li++){
        vector<uint32_t> nw(nc); bool alive=true;
        for(int j=0;j<nc;j++){ uint32_t v=pool[i*nc+j]; int tape=v>>8,ptr=(v>>1)&127,S=v&1;
          if(!runb(L[li],mode,tape,ptr,S,W)){alive=false;break;} nw[j]=(tape<<8)|(ptr<<1)|S; }
        if(!alive) continue; uint64_t h=hashv(nw.data()); if(!seen.insert(h).second) continue;
        pool.insert(pool.end(),nw.begin(),nw.end()); nodes.push_back({(int)i,(char)li});
        if(nw==exp){ string w; int k=nodes.size()-1; while(k>0){ w+=char('0'+nodes[k].letter); k=nodes[k].parent;} reverse(w.begin(),w.end()); printf("FOUND %d %s\n",(int)w.size(),w.c_str()); return 0; }
      }
      if(nodes.size()>(size_t)maxs){ printf("CAP depth %d states %zu\n",d,nodes.size()); return 0; }
    }
    fs=fe; fe=nodes.size(); if(fs==fe){ printf("EXHAUSTED depth %d states %zu\n",d,nodes.size()); return 0; }
  }
  printf("DEPTH states %zu\n",nodes.size()); return 0; }
