"""Named corner sets for the time-domain runs (override values apply to every instance)."""
CORNERS = {
    'nom': dict(mode='nom'),
    # slowest LDR/lamp, dim, dark effect on, worst strike loading
    'slow': dict(mode='nom', dark=True, over=dict(tau_r=20e-3, tau_f=60e-3, td0=20e-3, Rd=1e6, Rlit=10e3,
                                                  Vs=105., dark_dv=25., Vb=65., Iext=100e-6, VP=0.97, Rtol=0.05, gamma=0.9)),
    # fastest LDR/lamp (least low-pass filtering), bright, primed
    'fast': dict(mode='nom', dark=False, over=dict(tau_r=5e-3, tau_f=20e-3, td0=1e-3, Rd=10e6, Rlit=1e3,
                                                   Vs=85., Vb=55., Iext=20e-6, VP=1.03, Rtol=-0.05, gamma=0.7)),
    # strong LDR dark leakage at weak light, high strike: hold/strike limit
    'weak': dict(mode='nom', dark=True, over=dict(Rd=1e6, Rlit=10e3, Vs=105., dark_dv=25., VP=0.97, Rtol=0.05)),
    # high lit current, low burning voltage: quench limit
    'hot':  dict(mode='nom', dark=False, over=dict(Vb=55., Iext=100e-6, Vs=85., VP=1.03, Rtol=-0.05, Rlit=10e3)),
}
def vertex(seed): return dict(mode='vertex', dark=True, seed=seed)
