Param($src_dir, $dst_dir)

#$files = ls "$src_dir" -Recurse | ?{ ($_.BaseName -like "*toc") -and ($_.Extension -eq ".html" -or $_.Extension -eq ".htm") };
$files = ls "$src_dir\*" -Recurse | ?{ ($_.Extension -eq ".hhc") };
write-host "找到 $($files.Count) 个hhc文件。"

foreach ($file in $files) {
    $src_path = $file.FullName;
    $src_dir = $file.DirectoryName;
    $src_fn = $file.BaseName;

    $dst_path = Join-Path $dst_dir ($src_dir.Substring($src_dir.LastIndexOf('\') + 1) + ".pdf");
    Write-Host "正在处理: $src_path => $dst_path"
  

#    & python .\src\format_convert.py $src_path $dst_path;
}