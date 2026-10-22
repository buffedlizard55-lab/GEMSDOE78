#!/usr/bin/env python3
"""Quick test: lidar+raw19 vs H78-A steered holdout."""
import json, time, sys
from pathlib import Path
import numpy as np
import rasterio
from sklearn.metrics import roc_auc_score
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"vendor")); sys.path.insert(0,str(ROOT/"src"))
from gems57 import grid as G, holdout as HO, evaluate_holdout as EH
from gems78 import pipeline as P, emit as E, features as F, lidar as L

BUDGETS=[44090,50000]
HGB=dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=200, l2_regularization=1.0, max_bins=255, early_stopping=False, random_state=0)

def evaluate_dots(dots,folds,fp):
    pred=dots.astype(np.float32)
    terms=None; per={}
    for f in folds:
        r,t=EH.evaluate(pred,f,fp,block_side=200,origin=(0,0),global_shape=fp.shape)
        per[f["name"]]=r["dti"]
        terms=t if terms is None else terms+t
    return terms,per

def main():
    ap=__import__("argparse").ArgumentParser()
    ap.add_argument("--seed",type=int,default=20)
    args=ap.parse_args()
    g=G.load_grid(ROOT/"data/bridge"); fp=g.footprint
    folds,quad=HO.buffered_component_draw(g,seed=args.seed,hide_frac=0.20,buffer_px=3)
    visible=folds[0]["visible"]
    tag=f"seed{args.seed}"
    feats_path,fmeta=P.build_feature_matrix(tag,fp,visible)
    print("base ready")
    lidar_stack,_=L.load_lidar_stack()
    lidar_fp=L.extract_lidar_for_footprint(lidar_stack,fp)
    base_mm=np.load(feats_path,mmap_mode="r")
    # names
    base_names=F.feature_names(iso=True,steered=True) #103
    lidar_names=L.lidar_feature_names() #12
    all_names=base_names+lidar_names
    # training sample
    pos,negs=P.training_sample(fp,visible,450_000,seed=args.seed)
    rows_pos,rows_neg=P.flat_to_rows(pos,fp),P.flat_to_rows(negs,fp)
    # helper
    def arm_cols(arm):
        if arm=="A2_h78_steered":
            return np.array([i for i,n in enumerate(all_names) if n in F.feature_names(iso=True,steered=True)],dtype=np.int64)
        elif arm=="A_raw_lidar":
            # raw19 + lidar 12
            raw_names=F.feature_names(iso=False,steered=False)
            cols=[i for i,n in enumerate(all_names) if n in raw_names]
            cols+=[i for i,n in enumerate(all_names) if n in lidar_names]
            return np.array(cols,dtype=np.int64)
        elif arm=="A_lidar_only":
            return np.array([i for i,n in enumerate(all_names) if n in lidar_names],dtype=np.int64)
        else: raise ValueError(arm)
    from sklearn.ensemble import HistGradientBoostingClassifier
    def fit(arm):
        cols=arm_cols(arm)
        base_cols=[c for c in cols if c<103]
        lidar_cols=[c-103 for c in cols if c>=103]
        rows=np.concatenate([rows_pos,rows_neg])
        order=np.argsort(rows)
        if base_cols and lidar_cols:
            Xb=np.asarray(base_mm[rows[order]][:,base_cols],np.float32)
            Xl=lidar_fp[rows[order]][:,lidar_cols]
            X=np.concatenate([Xb,Xl],axis=1)
        elif base_cols:
            X=np.asarray(base_mm[rows[order]][:,base_cols],np.float32)
        else:
            X=lidar_fp[rows[order]][:,lidar_cols]
        y=np.concatenate([np.ones(rows_pos.size,np.int8),np.zeros(rows_neg.size,np.int8)])[order]
        clf=HistGradientBoostingClassifier(**HGB)
        clf.fit(X,y)
        return clf,cols
    def score_grid(clf,cols):
        n=base_mm.shape[0]; out=np.zeros(n,np.float32)
        base_cols=[c for c in cols if c<103]
        lidar_cols=[c-103 for c in cols if c>=103]
        for lo in range(0,n,600_000):
            hi=min(n,lo+600_000)
            if base_cols and lidar_cols:
                Xb=np.asarray(base_mm[lo:hi][:,base_cols],np.float32)
                Xl=lidar_fp[lo:hi][:,lidar_cols]
                X=np.concatenate([Xb,Xl],axis=1)
            elif base_cols:
                X=np.asarray(base_mm[lo:hi][:,base_cols],np.float32)
            else:
                X=lidar_fp[lo:hi][:,lidar_cols]
            out[lo:hi]=clf.predict_proba(X)[:,1].astype(np.float32)
        grid=np.zeros(fp.shape,np.float32); grid[fp]=out
        return grid

    arms=["A2_h78_steered","A_raw_lidar","A_lidar_only"]
    results={}
    terms_by_arm={}
    for arm in arms:
        clf,cols=fit(arm)
        s=score_grid(clf,cols)
        print(f"fit {arm} cols {len(cols)}")
        for n in BUDGETS:
            # B3 flank
            allowed=fp & ~E.flank_mask(visible,3.0)
            rank=E.greedy_dots(s,allowed,min_dist=2.8,max_dots=max(BUDGETS))
            dots=E.prefix(rank,n)
            t,per=evaluate_dots(dots,folds,fp)
            pooled=float(EH.from_terms(t.sum(axis=0)))
            key=f"{arm}|B3|{n}"
            terms_by_arm[key]=t
            print(f" {key} {pooled:.4f} per {per}")
            if arm not in results: results[arm]={}
            results[arm][n]=pooled
    # also test A0 for reference
    # quick pooled summary
    cand=max(terms_by_arm, key=lambda k: EH.from_terms(terms_by_arm[k].sum(axis=0)))
    print("best",cand, EH.from_terms(terms_by_arm[cand].sum(axis=0)))

if __name__=="__main__": main()
