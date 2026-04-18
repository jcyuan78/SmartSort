Param($src_dir, $dst_dir)

#$files = Get-ChildItem -Path $src_dir -Filter *.chm -Recurse
$files = ls "$src_dir\*.chm";
foreach ($file in $files) {
    $src_path = $file.FullName;
    $src_dir = $file.DirectoryName;
    $src_fn = $file.BaseName;

    # 处理包含中文字符的文件路径
#    $ext = [System.IO.Path]::GetExtension($file.Name)
      
    # 简单方案：使用 Base64 编码的前 8 位代替中文，确保唯一性且为英文
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($src_fn)
    $encoded = [Convert]::ToBase64String($bytes) -replace '[/+=]', ''
    $new_base_name = "ZH_" + $encoded.Substring(0, [math]::Min(8, $encoded.Length))

#    $target = join-path $dst_dir $src_fn;

    $dst_path = join-path $dst_dir $new_base_name
    Write-Host "正在处理: $src_path => $dst_path" -ForegroundColor Yellow
    & python .\src/extra_chm.py $src_path $dst_path

    $files = ls "$dst_path\*" -Recurse | ?{ ($_.Extension -eq ".hhc") };
    if ($files.Count -eq 0) {
        write-host "$src_fn 中未找到hhc文件，跳过" -ForegroundColor Cyan;
        continue
    }
    elseif ($files.Count -gt 1) {
        write-host "$src_fn 中找到多个hhc文件，可能存在问题，请检查" -ForegroundColor Yellow;
        $index = 1;
        foreach ($file in $files) {
            $hhc_file = $file.FullName;
    #        $src_dir = $file.DirectoryName;
    #        $src_fn = $file.BaseName;

            $target = Join-Path $dst_dir "$src_fn-$index.pdf";
            Write-Host "格式转换: $hhc_file => $dst_path"
        
            & python .\src\format_convert.py $hhc_file $dst_path;
            $index += 1;
        }
    }
    else {
        $hhc_file = $files[0].FullName;
        $target = Join-Path $dst_dir ($src_fn + ".pdf");
        Write-Host "格式转换: $hhc_file => $target" -ForegroundColor Yellow
        & python .\src\format_convert.py $hhc_file $target;
    }

    if ($dst_path -ne $target) {
        mv $dst_path $target -Force
        write-host "重命名: $dst_path -> $target"
    }
}
