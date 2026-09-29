// exhaustive menu search: which bundle menus admit exact transparent macros
// FLIP NEXT PREV IF END (see macro.py).  usage: msearch K MODE L PART NPARTS [gmax]
#include <bits/stdc++.h>
using namespace std;
struct Bd { vector<char> ops; bool mark; string name; };  // ops: F,0,1 (tests),P,M
struct Enc { string name; int g; int tab[2]; };
vector<Bd> BD; vector<Enc> ENC;
static inline bool runb(const Bd& b, int mode, int& tape, int& ptr, int& S, int W){
  if (S){ if(!b.mark) return true; if(mode==0){S=0; return true;} }
  int S2=0;
  for(char op: b.ops){
    if(op=='F') tape^=1<<ptr;
    else if(op=='0'||op=='1'){ if(((tape>>ptr)&1)==(op-'0')) S2=1; }
    else { ptr += (op=='P')?1:-1; if(ptr<0||ptr>=W) return false; }
  }
  S=S2; return true;
}
string bname(const Bd&b){ string s="("; for(size_t i=0;i<b.ops.size();i++){ if(i) s+=","; char c=b.ops[i]; if(c=='0')s+="T0"; else if(c=='1')s+="T1"; else s+=c;} if(b.mark) s+="+K"; return s+")"; }
void gen(){
  const char* Fs[]={"","F"}; 
  vector<string> ts={"","0","1"}, ms={"","P","M"};
  for(int f=0;f<2;f++)for(auto&t:ts)for(auto&m:ms){
    vector<char> items; if(f) items.push_back('F'); if(!t.empty()) items.push_back(t[0]); if(!m.empty()) items.push_back(m[0]);
    sort(items.begin(),items.end()); set<vector<char>> seen;
    do{ if(seen.count(items)) continue; seen.insert(items);
      { bool mv=false, bad=false; for(char c: items){ if(c=='P'||c=='M') mv=true; else if(mv) bad=true; } if(bad) continue; }
      for(int k=0;k<2;k++){ if(items.empty()&&!k) continue; Bd b; b.ops=items; b.mark=k; b.name=bname(b); BD.push_back(b);} }
    while(next_permutation(items.begin(),items.end()));
  }
}
int cover(const vector<int>& menu){ int c=0; for(int i:menu){ auto&b=BD[i]; for(char o:b.ops){ if(o=='F')c|=1; else if(o=='0'||o=='1')c|=2; else if(o=='P')c|=4; else c|=8;} if(b.mark)c|=16;} return c; }
// symmetry: mirror P<->M, complement 0<->1
vector<int> BDsym[4];
int findb(const Bd& x){ for(size_t i=0;i<BD.size();i++) if(BD[i].ops==x.ops&&BD[i].mark==x.mark) return i; return -1; }
int main(int argc,char**argv){
  int K=atoi(argv[1]), mode=atoi(argv[2]), L=atoi(argv[3]), part=atoi(argv[4]), np=atoi(argv[5]); int gmax= argc>6?atoi(argv[6]):3;
  gen();
  { ifstream f("enc.txt"); string n; int g,a,b; while(f>>n>>g>>a>>b){ if(g<=gmax) ENC.push_back({n,g,{a,b}}); } }
  for(int s=0;s<4;s++){ BDsym[s].resize(BD.size()); for(size_t i=0;i<BD.size();i++){ Bd x=BD[i]; for(auto&c:x.ops){ if((s&1)&&(c=='P'||c=='M')) c=(c=='P')?'M':'P'; if((s&2)&&(c=='0'||c=='1')) c=(c=='0')?'1':'0'; } BDsym[s][i]=findb(x);} }
  int nb=BD.size(); fprintf(stderr,"bundles %d encs %zu\n",nb,ENC.size());
  vector<int> idx(K); long cnt=0, tested=0;
  function<void(int,int)> rec=[&](int d,int start){
    if(d==K){
      if(cover(idx)!=31) return;
      // canonical under symmetry
      for(int s=1;s<4;s++){ vector<int> v; for(int i:idx) v.push_back(BDsym[s][i]); sort(v.begin(),v.end()); if(v<idx) return; }
      if((cnt++ % np)!=part) return;
      tested++;
      vector<const Bd*> let; for(int i:idx) let.push_back(&BD[i]);
      for(auto& e: ENC) for(int rest=0;rest<e.g;rest++){
        int g=e.g, ng=3, W=ng*g, p0=g+rest;
        // conditions
        vector<int> t0s; for(int c=0;c<8;c++){ int t=0; for(int i=0;i<3;i++){ int x=(c>>i)&1; t|= e.tab[x]<<(i*g);} t0s.push_back(t);}
        int nc=16; vector<uint32_t> init(nc);
        for(int c=0;c<8;c++) for(int S=0;S<2;S++) init[2*c+S]=(t0s[c]<<8)|(p0<<1)|S;
        // pack: tape up to 12 bits: shift 8 -> ok in 32 bits
        int found[5]={-1,-1,-1,-1,-1}; vector<int> fw[5];
        unordered_set<string> seen; 
        auto key=[&](const vector<uint32_t>&v){ return string((const char*)v.data(), v.size()*4); };
        seen.insert(key(init));
        vector<pair<vector<int>,vector<uint32_t>>> fr; fr.push_back({{},init});
        auto check=[&](const vector<int>&w,const vector<uint32_t>&st){
          for(int pr=0;pr<5;pr++){ if(found[pr]>=0) continue; bool ok=true;
            for(int c=0;c<8&&ok;c++){ uint32_t s0=st[2*c], s1=st[2*c+1]; uint32_t i0=(t0s[c]<<8)|(p0<<1);
              int x=(c>>1)&1;
              if(pr==4){ if(s0!=i0||s1!=i0) ok=false; continue; }
              if(s1!=(i0|1)) {ok=false;continue;}
              uint32_t exp;
              if(pr==0){ int c2=c^2; int t2=0; for(int i=0;i<3;i++){int xx=(c2>>i)&1; t2|=e.tab[xx]<<(i*g);} exp=(t2<<8)|(p0<<1); }
              else if(pr==1) exp=(t0s[c]<<8)|((p0+g)<<1);
              else if(pr==2) exp=(t0s[c]<<8)|((p0-g)<<1);
              else exp=i0|(x==0?1:0);
              if(s0!=exp) ok=false; }
            if(ok){ found[pr]=w.size(); fw[pr]=w; } }
        };
        for(int depth=1;depth<=L;depth++){
          vector<pair<vector<int>,vector<uint32_t>>> nx;
          for(auto& [w,st]: fr) for(int li=0;li<K;li++){
            vector<uint32_t> nw(nc); bool alive=true;
            for(int j=0;j<nc&&alive;j++){ int tape=st[j]>>8, ptr=(st[j]>>1)&127, S=st[j]&1;
              if(!runb(*let[li],mode,tape,ptr,S,W)){alive=false;break;} nw[j]=(tape<<8)|(ptr<<1)|S; }
            if(!alive) continue; string k=key(nw); if(!seen.insert(k).second) continue;
            vector<int> w2=w; w2.push_back(li); check(w2,nw); nx.push_back({w2,nw}); }
          fr.swap(nx);
          bool all=true; for(int p=0;p<5;p++) if(found[p]<0) all=false;
          if(all||fr.empty()) break; }
        bool all=true; int tot=0; for(int p=0;p<5;p++){ if(found[p]<0) all=false; else tot+=found[p]; }
        if(all){ printf("OK"); for(int i:idx) printf(" %s",BD[i].name.c_str()); printf(" | %s g=%d rest=%d tot=%d |",e.name.c_str(),g,rest,tot);
          const char* pn[5]={"FLIP","NEXT","PREV","IF","END"}; for(int p=0;p<5;p++){ printf(" %s=",pn[p]); for(int l:fw[p]) printf("%d",l);} printf("\n"); fflush(stdout); }
      }
      return; }
    for(int i=start;i<nb;i++){ idx[d]=i; rec(d+1,i+1); }
  };
  rec(0,0);
  fprintf(stderr,"K=%d part %d: tested %ld menus\n",K,part,tested);
}
