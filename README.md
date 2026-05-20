# Tree Mesh Reconstruction from Point Clouds

Failure-mode analysis of [AdTree](https://github.com/tudelft3d/AdTree) as a method
for reconstructing 3D tree meshes from sparse point clouds.

This repository accompanies the seminar work for the course
**Advanced Computer Graphics (NRG)**, Faculty of Computer and Information Science,
University of Ljubljana, academic year 2025/26 — seminar topic **2.14 Tree mesh
reconstruction from point clouds**.

## Overview

The aim of this work is to thoroughly examine a single tree-mesh reconstruction
method ([AdTree, Du et al. 2019][adtree-paper]) on a controlled benchmark of
synthetic and real tree point clouds, identify the inputs and conditions under
which it fails, and propose and evaluate concrete improvements to its
reconstruction quality.

The contributions of this repository are:

1. A small benchmark of 4 synthetic trees (procedurally generated with known
   ground-truth meshes) and 4 real tree point clouds borrowed from the AdTree
   paper.
2. A Python evaluation pipeline that computes Chamfer distance, Hausdorff
   distance, precision / recall / F-score at configurable thresholds, and an
   approximate voxel Intersection-over-Union (IoU) between a predicted and a
   ground-truth mesh.
3. A reproducible PowerShell script that runs the full evaluation sweep over
   sample sizes and F-thresholds, and a Python aggregator that summarises the
   resulting per-run CSVs into a single report-ready table.

Improvements to AdTree and the systematic failure-mode study described in the
accompanying report are wrapped around AdTree as pre- and post-processing
steps; the AdTree binary itself is used unmodified.

## Repository structure

```
tree-mesh-reconstruction-from-point-clouds/
├── data/
│   ├── real/
│   │   ├── xyz/              # Real tree point clouds (from AdTree paper)
│   │   └── adtree_output/    # AdTree reconstructions for the real trees
│   └── synthetic/
│       ├── gt_mesh/          # Procedurally generated ground-truth meshes (.obj)
│       ├── point_cloud/      # Point clouds sampled from the ground-truth meshes
│       └── adtree_output/    # AdTree reconstructions for the synthetic trees
├── results/
│   ├── metrics/              # Per-run evaluation CSVs (one per setting)
│   ├── heatmaps/             # Coloured PLY error heatmaps
│   ├── summary_full.csv      # All runs combined (generated)
│   ├── summary.csv           # Canonical view, 100k points, F=0.10 (generated)
│   └── summary.md            # Same as summary.csv, in Markdown (generated)
├── scripts/
│   ├── sample_mesh_to_xyz.py        # GT mesh -> .xyz point cloud
│   ├── evaluate_mesh.py             # Compute metrics for one (gt, pred) pair
│   ├── aggregate_results.py         # Combine per-run CSVs into a summary
│   ├── view_xyz.py                  # Quick Open3D viewer for .xyz files
│   ├── xyz_stats.py                 # Bounding box / centre / count stats
│   └── run_synthetic_evaluations.ps1  # PowerShell driver for the full sweep
├── README.md
├── LICENSE                    # MIT
├── requirements.txt
└── .gitignore
```

AdTree itself is **not** vendored into this repository. It is used as an
external tool — see [Setup](#setup) below.

## Requirements

* Python 3.10 or newer
* AdTree (prebuilt Windows binary v1.1.2 used in this work)
* Optional: Blender 3.x or newer if you want to (re)generate synthetic
  ground-truth trees
* Optional: MeshLab or Blender for inspecting the reconstructed `.obj` meshes

Python dependencies (see `requirements.txt`):

```
numpy
open3d
scipy
trimesh
pandas
pillow
matplotlib
```

Install with:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Setup

### 1. AdTree binary

Download AdTree v1.1.2 from
<https://github.com/tudelft3d/AdTree/releases/tag/v1.1.2> and extract it
somewhere outside this repository, e.g. `..\Tools\AdTree-v1.1.2_for_Windows\`.

Verify the binary works in command-line mode (GUI mode requires a working
OpenGL stack and is not needed here):

```powershell
.\AdTree.exe path\to\tree.xyz path\to\output_dir -s
```

### 2. Point cloud expectations

AdTree expects each input `.xyz` file to:

* contain a **single segmented tree** (no ground, no other objects);
* have an **upright orientation** with the Z axis pointing up.

The `sample_mesh_to_xyz.py` script automatically converts Blender's default
Y-up coordinate system to Z-up. The `evaluate_mesh.py` script does the same
defensively when loading meshes for evaluation.

## Reproducing the results

The following steps reproduce the synthetic-tree evaluation reported in the
seminar. All commands assume the repository root as the working directory.

### Step 1 — Sample point clouds from ground-truth meshes (optional)

The repository already ships with sampled `.xyz` files in
`data/synthetic/point_cloud/`. To re-sample them from the ground-truth
meshes (e.g. with a different point count), use:

```powershell
python scripts/sample_mesh_to_xyz.py `
    --mesh data/synthetic/gt_mesh/synthetic_01_gt.obj `
    --out  data/synthetic/point_cloud/synthetic_01.xyz `
    --points 50000
```

### Step 2 — Run AdTree on each synthetic point cloud

Either point AdTree at the entire synthetic point-cloud directory in batch
mode:

```powershell
..\Tools\AdTree-v1.1.2_for_Windows\AdTree.exe `
    data/synthetic/point_cloud `
    data/synthetic/adtree_output `
    -s
```

…or process trees one by one. The `adtree_output/` directory is populated with
`*_branches.obj` and (with `-s`) `*_skeleton.ply` files.

> AdTree also generates a `*_leaves.obj` file in some configurations. AdTree's
> "leaves" are not reconstructed from the input cloud — they are random
> billboard quads placed at skeleton endpoints — so they are not used in the
> quantitative evaluation here.

### Step 3 — Evaluate one (ground truth, prediction) pair

For a single tree:

```powershell
python scripts/evaluate_mesh.py `
    --gt   data/synthetic/gt_mesh/synthetic_01_gt.obj `
    --pred data/synthetic/adtree_output/synthetic_01_branches.obj `
    --points 100000 `
    --f-threshold 0.10 `
    --voxel-size 0.10 `
    --out results/metrics/synthetic_01_100000_sample_points_f0.10_v0.10.csv `
    --heatmap-out results/heatmaps/synthetic_01_100000_sample_points_heatmap_max0.20.ply `
    --heatmap-max-distance 0.20
```

### Step 4 — Run the full synthetic sweep

The PowerShell driver runs steps 3 for all 4 synthetic trees at sample sizes
{50000, 75000, 100000} and F-thresholds {0.05, 0.10, 0.20} (36 runs total):

```powershell
scripts/run_synthetic_evaluations.ps1
```

### Step 5 — Aggregate results

Combine all per-run CSVs in `results/metrics/` into a single summary table and
print a Markdown view of the canonical setting (100 000 sampled points,
F-threshold 0.10 m):

```powershell
python scripts/aggregate_results.py --write-markdown
```

This writes `results/summary_full.csv` (all 36 rows) and `results/summary.csv`
+ `results/summary.md` (canonical 4-row view).

## Current baseline results

Synthetic trees, 100 000 sampled points, F-score threshold 0.10 m,
voxel size 0.10 m:

| tree | chamfer_distance | hausdorff_distance | precision | recall | f_score | voxel_iou |
|---|---|---|---|---|---|---|
| synthetic_01 | 0.0880 | 0.5928 | 0.8352 | 0.9835 | 0.9033 | 0.5120 |
| synthetic_02 | 0.0541 | 0.3653 | 0.9952 | 0.9851 | 0.9901 | 0.6833 |
| synthetic_03 | 0.0587 | 1.3044 | 0.9965 | 0.9726 | 0.9844 | 0.6779 |
| synthetic_04 | 0.0398 | 0.2318 | 0.9872 | 0.9959 | 0.9915 | 0.7205 |

Distances are reported in the model's native units. The synthetic trees are
modelled at metric scale, so values can be read directly in metres.

The real trees do not have a paired ground-truth mesh, so they are evaluated
only qualitatively (rendered reconstructions in the seminar report).

## Notes and limitations

* **Leaves are not evaluated.** AdTree's leaf output is a heuristic decorative
  layer, not a reconstruction. Evaluation focuses on the branch mesh
  (`*_branches.obj`) against ground truth.
* **Real-tree evaluation is qualitative only.** The four real point clouds
  (tree1, tree33, almere-001, house) reused from the AdTree paper do not have
  paired ground-truth meshes, so they are used for visual comparison rather
  than for the numerical sweep.
* **`house.xyz` is intentionally not a tree.** It is kept as an
  out-of-distribution example to illustrate how AdTree behaves on inputs that
  violate its single-tree assumption. See the seminar report for details.
* **Up-axis handling.** Blender's OBJ exporter is Y-up by default, while
  AdTree assumes Z-up. Both `sample_mesh_to_xyz.py` and `evaluate_mesh.py`
  detect and correct this automatically.

## Citation

If you build on this work, please cite the original AdTree paper:

```
@article{du2019adtree,
  title   = {AdTree: Accurate, Detailed, and Automatic Modelling of Laser-Scanned Trees},
  author  = {Du, Shenglan and Lindenbergh, Roderik and Ledoux, Hugo and Stoter, Jantien and Nan, Liangliang},
  journal = {Remote Sensing},
  volume  = {11},
  number  = {18},
  pages   = {2074},
  year    = {2019}
}
```

## License

The code in this repository is released under the **MIT License**; see
[`LICENSE`](LICENSE).

AdTree itself is distributed by its authors under the GNU GPL v3 and is used
here as an unmodified external binary; it is not included in this repository.

## Acknowledgements

Original AdTree implementation by the
[3D Geoinformation Research Group, TU Delft](https://3d.bk.tudelft.nl/).
Seminar topic supervised by the Advanced Computer Graphics teaching team at
UL FRI.

[adtree-paper]: https://3d.bk.tudelft.nl/liangliang/publications/2019/adtree/AdTree_RS-2019.pdf
