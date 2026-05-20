$samplePointsList = @(50000, 75000, 100000)
$thresholds = @("0.05", "0.10", "0.20")

$voxelSize = "0.10"
$heatmapMaxDistance = "0.20"

New-Item -ItemType Directory -Force -Path "results/metrics" | Out-Null
New-Item -ItemType Directory -Force -Path "results/heatmaps" | Out-Null

foreach ($i in 1..4) {
    $id = "{0:D2}" -f $i

    foreach ($samplePoints in $samplePointsList) {
        foreach ($threshold in $thresholds) {
            $gt = "data/synthetic/gt_mesh/synthetic_${id}_gt.obj"
            $pred = "data/synthetic/adtree_output/synthetic_${id}_branches.obj"

            $out = "results/metrics/synthetic_${id}_${samplePoints}_sample_points_f${threshold}_v${voxelSize}.csv"

            Write-Host ""
            Write-Host "========================================"
            Write-Host "Evaluating synthetic_${id}"
            Write-Host "Sample points:          $samplePoints"
            Write-Host "F-threshold:            $threshold"
            Write-Host "Voxel size:             $voxelSize"
            Write-Host "GT:                     $gt"
            Write-Host "Pred:                   $pred"
            Write-Host "Out:                    $out"
            Write-Host "========================================"
            Write-Host ""

            # Heatmap is independent of the F-score threshold, so we only save it once
            # for the canonical setting: 100000 sampled points and f-threshold 0.10.
            if (($samplePoints -eq 100000) -and ($threshold -eq "0.10")) {
                $heatmapOut = "results/heatmaps/synthetic_${id}_${samplePoints}_sample_points_heatmap_max${heatmapMaxDistance}.ply"

                python scripts/evaluate_mesh.py `
                    --gt $gt `
                    --pred $pred `
                    --points $samplePoints `
                    --f-threshold $threshold `
                    --voxel-size $voxelSize `
                    --out $out `
                    --heatmap-out $heatmapOut `
                    --heatmap-max-distance $heatmapMaxDistance
            }
            else {
                python scripts/evaluate_mesh.py `
                    --gt $gt `
                    --pred $pred `
                    --points $samplePoints `
                    --f-threshold $threshold `
                    --voxel-size $voxelSize `
                    --out $out
            }
        }
    }
}