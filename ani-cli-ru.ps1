#!/usr/bin/env pwsh

$ErrorActionPreference = 'Stop'

$script:VERSION = '1.1.0'
$script:LANGUAGE = if ($env:ANI_CLI_LANG) { $env:ANI_CLI_LANG } else { 'ru' }
$script:QUALITY = if ($env:ANI_CLI_QUALITY) { $env:ANI_CLI_QUALITY } else { 'best' }
$script:STREAM_TYPE = if ($env:ANI_CLI_STREAM_TYPE) { $env:ANI_CLI_STREAM_TYPE } else { 'dub' }
$script:PLAYER = if ($env:ANI_CLI_PLAYER) { $env:ANI_CLI_PLAYER } else { '' }
$script:MENU_BACKEND = if ($env:ANI_CLI_EXTERNAL_MENU) { $env:ANI_CLI_EXTERNAL_MENU } else { 'fzf' }
$script:DOWNLOAD_DIR = if ($env:ANI_CLI_DOWNLOAD_DIR) { $env:ANI_CLI_DOWNLOAD_DIR } else { (Get-Location).Path }

if ($env:ANI_CLI_HIST_DIR) {
    $script:HIST_DIR = $env:ANI_CLI_HIST_DIR
} elseif ($env:LOCALAPPDATA) {
    $script:HIST_DIR = Join-Path $env:LOCALAPPDATA 'ani-cli-ru'
} else {
    $script:HIST_DIR = Join-Path $HOME '.ani-cli-ru'
}

$script:LOG_ENABLED = if ($env:ANI_CLI_LOG) { $env:ANI_CLI_LOG } else { '1' }
$script:API_BASE = if ($env:ANI_CLI_API_BASE) { $env:ANI_CLI_API_BASE } else { 'https://api.anilibria.app/api/v1' }
$script:API_MODE = if ($env:ANI_CLI_API_MODE) { $env:ANI_CLI_API_MODE } else { 'auto' }
$script:USER_AGENT = "ani-cli-ru/$($script:VERSION)"

$script:DOWNLOAD_MODE = $false
$script:SHOW_LOG = $false
$script:DELETE_LOG = $false
$script:PLAYER_FORCED = $false
$script:SUBTITLE_FALLBACK_WARNED = $false
$script:EPISODE_ARG = ''
$script:RANGE_ARG = ''
$script:QUERY = ''
$script:HIST_FILE = ''
$script:DOWNLOADER = ''

$script:Messages = @{
    ru = @{
        error                = 'Ошибка'
        warning              = 'Предупреждение'
        no_results           = 'Ничего не найдено'
        select_title         = 'Выберите аниме'
        select_episode       = 'Выберите эпизод'
        prompt_query         = 'Поиск аниме: '
        playing              = 'Проигрывание'
        downloading          = 'Загрузка'
        history_empty        = 'История пуста'
        history_deleted      = 'История очищена'
        history_header       = 'История просмотра'
        invalid_quality      = 'Недопустимое качество. Используйте: best, worst, 360p, 480p, 720p, 1080p'
        invalid_lang         = 'Недопустимый язык. Используйте: ru или en'
        invalid_range        = 'Недопустимый диапазон эпизодов. Используйте формат N-M'
        invalid_episode      = 'Недопустимый номер эпизода'
        episode_unavailable  = 'Эпизод недоступен'
        need_menu            = 'Для интерактивного выбора нужен fzf'
        need_player          = 'Не найден поддерживаемый плеер (mpv.exe, vlc.exe, mpv, vlc, iina)'
        need_downloader      = 'Для загрузки нужен aria2c, wget или встроенный Invoke-WebRequest'
        need_dep             = 'Отсутствует зависимость'
        stream_missing       = 'Не удалось получить ссылку потока для выбранного эпизода'
        sub_fallback         = 'Субтитры недоступны для этого релиза, используется обычный поток'
        non_interactive_pick = 'Неинтерактивный режим: автоматический выбор результата'
        api_failed           = 'Ошибка запроса к AniLibria API'
        api_deprecated       = 'Текущая версия API недоступна. Укажите актуальную через ANI_CLI_API_BASE.'
        unknown_option       = 'Неизвестный параметр'
        choose_query         = 'Укажите поисковый запрос'
        episode_word         = 'Эпизод'
        download_saved       = 'Сохранено'
        invalid_choice       = 'Некорректный выбор'
    }
    en = @{
        error                = 'Error'
        warning              = 'Warning'
        no_results           = 'No results found'
        select_title         = 'Select anime'
        select_episode       = 'Select episode'
        prompt_query         = 'Search anime: '
        playing              = 'Playing'
        downloading          = 'Downloading'
        history_empty        = 'History is empty'
        history_deleted      = 'History cleared'
        history_header       = 'Watch history'
        invalid_quality      = 'Invalid quality. Use: best, worst, 360p, 480p, 720p, 1080p'
        invalid_lang         = 'Invalid language. Use: ru or en'
        invalid_range        = 'Invalid episode range. Use N-M'
        invalid_episode      = 'Invalid episode number'
        episode_unavailable  = 'Episode is not available'
        need_menu            = 'Interactive selection requires fzf'
        need_player          = 'No supported player found (mpv.exe, vlc.exe, mpv, vlc, iina)'
        need_downloader      = 'Download mode requires aria2c, wget, or built-in Invoke-WebRequest'
        need_dep             = 'Missing dependency'
        stream_missing       = 'Failed to resolve a stream URL for selected episode'
        sub_fallback         = 'Subtitles stream is unavailable for this title, using default stream'
        non_interactive_pick = 'Non-interactive session: auto-selecting a result'
        api_failed           = 'AniLibria API request failed'
        api_deprecated       = 'Configured API version is unavailable. Set ANI_CLI_API_BASE to a working endpoint.'
        unknown_option       = 'Unknown option'
        choose_query         = 'Provide a search query'
        episode_word         = 'Episode'
        download_saved       = 'Saved'
        invalid_choice       = 'Invalid selection'
    }
}

function Lower {
    param([string]$Text)
    if ($null -eq $Text) { return '' }
    return $Text.ToLowerInvariant()
}

function Trim-Value {
    param([string]$Text)
    if ($null -eq $Text) { return '' }
    return $Text.Trim()
}

function Has-Command {
    param([string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) { return $false }
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Msg {
    param([string]$Key)

    $lang = Lower $script:LANGUAGE
    if (-not $script:Messages.ContainsKey($lang)) {
        $lang = 'en'
    }

    $table = $script:Messages[$lang]
    if ($table.ContainsKey($Key)) {
        return [string]$table[$Key]
    }

    return $Key
}

function Die {
    param([string]$Text)
    [Console]::Error.WriteLine("{0}: {1}" -f (Msg 'error'), $Text)
    exit 1
}

function Warn {
    param([string]$Text)
    [Console]::Error.WriteLine("{0}: {1}" -f (Msg 'warning'), $Text)
}

function Print-Help {
    if ((Lower $script:LANGUAGE) -eq 'ru') {
@"
Использование:
  ./ani-cli-ru.ps1 [опции] "поисковый запрос"

Опции:
  -h, --help             Показать справку
  -v, --version          Показать версию
  -q, --quality Q        Качество: best|worst|360p|480p|720p|1080p
  -d, --download         Режим загрузки
  -e, --episode N        Номер эпизода
  -r, --range N-M        Диапазон эпизодов
  -l, --logview          Показать историю просмотра
  -D, --delete           Очистить историю просмотра
  --lang ru|en           Язык интерфейса
  --sub                  Запросить поток с субтитрами (если доступен)
  --vlc                  Использовать VLC

Переменные окружения:
  ANI_CLI_LANG           Язык интерфейса (ru|en)
  ANI_CLI_PLAYER         Плеер (mpv.exe|vlc.exe|mpv|vlc|iina)
  ANI_CLI_QUALITY        Качество по умолчанию
  ANI_CLI_STREAM_TYPE    Тип потока (dub|sub)
  ANI_CLI_DOWNLOAD_DIR   Каталог для загрузок
  ANI_CLI_HIST_DIR       Каталог истории
  ANI_CLI_LOG            Включить лог (1|0)
  ANI_CLI_EXTERNAL_MENU  Меню (fzf)
  ANI_CLI_API_BASE       Базовый URL API
  ANI_CLI_API_MODE       Режим API (auto|v1|v3)

Примеры:
  ./ani-cli-ru.ps1 "атака титанов"
  ./ani-cli-ru.ps1 -q 720p "код гиас"
  ./ani-cli-ru.ps1 -e 5 "demon slayer"
  ./ani-cli-ru.ps1 -r 1-3 -d "one piece"
"@
    } else {
@"
Usage:
  ./ani-cli-ru.ps1 [options] "search query"

Options:
  -h, --help             Show help
  -v, --version          Show version
  -q, --quality Q        Quality: best|worst|360p|480p|720p|1080p
  -d, --download         Download mode
  -e, --episode N        Episode number
  -r, --range N-M        Episode range
  -l, --logview          Show watch history
  -D, --delete           Clear watch history
  --lang ru|en           UI language
  --sub                  Request subtitles stream (if available)
  --vlc                  Use VLC player

Environment variables:
  ANI_CLI_LANG           UI language (ru|en)
  ANI_CLI_PLAYER         Player (mpv.exe|vlc.exe|mpv|vlc|iina)
  ANI_CLI_QUALITY        Default quality
  ANI_CLI_STREAM_TYPE    Stream type (dub|sub)
  ANI_CLI_DOWNLOAD_DIR   Download directory
  ANI_CLI_HIST_DIR       History directory
  ANI_CLI_LOG            Enable logging (1|0)
  ANI_CLI_EXTERNAL_MENU  Menu backend (fzf)
  ANI_CLI_API_BASE       API base URL
  ANI_CLI_API_MODE       API mode (auto|v1|v3)

Examples:
  ./ani-cli-ru.ps1 "attack on titan"
  ./ani-cli-ru.ps1 -q 720p "code geass"
  ./ani-cli-ru.ps1 -e 5 "demon slayer"
  ./ani-cli-ru.ps1 -r 1-3 -d "one piece"
"@
    }
}

function Normalize-Lang {
    param([string]$Value)
    $v = Lower $Value
    if ($v -in @('ru', 'en')) {
        return $v
    }
    return ''
}

function Normalize-Quality {
    param([string]$Value)
    $q = Lower $Value
    switch ($q) {
        'best' { return 'best' }
        'auto' { return 'best' }
        'worst' { return 'worst' }
        '1080' { return '1080p' }
        '1080p' { return '1080p' }
        'fhd' { return '1080p' }
        'fullhd' { return '1080p' }
        '720' { return '720p' }
        '720p' { return '720p' }
        'hd' { return '720p' }
        '480' { return '480p' }
        '480p' { return '480p' }
        'sd' { return '480p' }
        '360' { return '360p' }
        '360p' { return '360p' }
        'ld' { return '360p' }
        'low' { return '360p' }
        default { return '' }
    }
}

function Ensure-History {
    if (-not (Test-Path -LiteralPath $script:HIST_DIR -PathType Container)) {
        New-Item -Path $script:HIST_DIR -ItemType Directory -Force | Out-Null
    }

    $script:HIST_FILE = Join-Path $script:HIST_DIR 'history.log'
    if (-not (Test-Path -LiteralPath $script:HIST_FILE -PathType Leaf)) {
        New-Item -Path $script:HIST_FILE -ItemType File -Force | Out-Null
    }
}

function Show-History {
    Ensure-History

    if (-not (Get-Item -LiteralPath $script:HIST_FILE).Length) {
        Write-Output (Msg 'history_empty')
        return
    }

    Write-Output ((Msg 'history_header') + ':')
    foreach ($line in Get-Content -LiteralPath $script:HIST_FILE) {
        $parts = $line -split "`t"
        if ($parts.Count -ge 6) {
            Write-Output ("{0} | {1} | ep {2} | {3} | {4}" -f $parts[0], $parts[2], $parts[3], $parts[4], $parts[5])
        } else {
            Write-Output $line
        }
    }
}

function Clear-History {
    Ensure-History
    Set-Content -LiteralPath $script:HIST_FILE -Value ''
    Write-Output (Msg 'history_deleted')
}

function Append-History {
    param(
        [string]$TitleId,
        [string]$TitleName,
        [string]$Episode,
        [string]$Quality,
        [string]$StreamType
    )

    if ($script:LOG_ENABLED -ne '1') {
        return
    }

    Ensure-History
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "{0}`t{1}`t{2}`t{3}`t{4}`t{5}" -f $ts, $TitleId, $TitleName, $Episode, $Quality, $StreamType
    Add-Content -LiteralPath $script:HIST_FILE -Value $line
}

function Ensure-MenuBackend {
    $backend = Lower $script:MENU_BACKEND
    if ($backend -eq '' -or $backend -eq 'fzf') {
        if (-not (Has-Command 'fzf')) {
            die ((Msg 'need_menu') + ': fzf')
        }
        $script:MENU_BACKEND = 'fzf'
        return
    }

    die ((Msg 'need_menu') + ': ' + $backend)
}

function Read-SelectionByNumber {
    param(
        [string[]]$Lines,
        [string]$Prompt
    )

    Write-Output ''
    Write-Output ($Prompt + ':')

    for ($i = 0; $i -lt $Lines.Count; $i++) {
        Write-Output ("[{0}] {1}" -f ($i + 1), $Lines[$i])
    }

    while ($true) {
        $raw = Read-Host ("1-{0}" -f $Lines.Count)
        if ([string]::IsNullOrWhiteSpace($raw)) {
            return $null
        }

        $idx = 0
        if ([int]::TryParse($raw, [ref]$idx) -and $idx -ge 1 -and $idx -le $Lines.Count) {
            return $Lines[$idx - 1]
        }

        Warn (Msg 'invalid_choice')
    }
}

function Select-Line {
    param(
        [string[]]$Lines,
        [string]$Prompt,
        [string]$Hint = ''
    )

    $clean = @($Lines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($clean.Count -eq 0) {
        return $null
    }

    if ($clean.Count -eq 1) {
        return $clean[0]
    }

    $isInputRedirected = $false
    try {
        $isInputRedirected = [Console]::IsInputRedirected
    } catch {
        $isInputRedirected = $false
    }

    if ($isInputRedirected) {
        Warn (Msg 'non_interactive_pick')
        if (-not [string]::IsNullOrWhiteSpace($Hint)) {
            foreach ($line in $clean) {
                if ($line -match [Regex]::Escape($Hint)) {
                    return $line
                }
            }
        }
        return $clean[0]
    }

    if ((Lower $script:MENU_BACKEND) -eq 'fzf' -and (Has-Command 'fzf')) {
        $selection = ($clean -join "`n") | & fzf --reverse --cycle --height=80% --prompt="$Prompt> "
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($selection)) {
            return [string]$selection
        }
        return $null
    }

    Read-SelectionByNumber -Lines $clean -Prompt $Prompt
}

function Detect-ApiMode {
    $mode = Lower $script:API_MODE
    switch ($mode) {
        'v1' {
            $script:API_MODE = 'v1'
            return
        }
        'v3' {
            $script:API_MODE = 'v3'
            return
        }
        'auto' { }
        '' { }
        default {
            Die 'ANI_CLI_API_MODE must be auto, v1 or v3'
        }
    }

    if ($script:API_BASE -match '/v3(/|$)' -or $script:API_BASE -match 'api\.anilibria\.tv') {
        $script:API_MODE = 'v3'
    } else {
        $script:API_MODE = 'v1'
    }
}

function Build-QueryString {
    param([hashtable]$Query)

    if ($null -eq $Query -or $Query.Count -eq 0) {
        return ''
    }

    $pairs = [System.Collections.Generic.List[string]]::new()
    foreach ($key in $Query.Keys) {
        $value = $Query[$key]
        if ($null -eq $value) {
            continue
        }

        $pairs.Add(("{0}={1}" -f [Uri]::EscapeDataString([string]$key), [Uri]::EscapeDataString([string]$value)))
    }

    return ($pairs -join '&')
}

function Try-ParseJson {
    param([string]$Body)

    if ([string]::IsNullOrWhiteSpace($Body)) {
        return $null
    }

    try {
        return $Body | ConvertFrom-Json -Depth 100
    } catch {
        return $null
    }
}

function Get-ApiErrorMessage {
    param($Parsed)

    if ($null -eq $Parsed) {
        return ''
    }

    if ($Parsed.PSObject.Properties['error']) {
        $err = $Parsed.error
        if ($null -ne $err -and $err.PSObject.Properties['message'] -and $err.message) {
            return [string]$err.message
        }
    }

    if ($Parsed.PSObject.Properties['message'] -and $Parsed.message) {
        return [string]$Parsed.message
    }

    return ''
}

function Invoke-ApiRequest {
    param(
        [string]$Endpoint,
        [hashtable]$Query = @{}
    )

    $base = $script:API_BASE.TrimEnd('/')
    $ep = $Endpoint.TrimStart('/')
    $uri = "$base/$ep"
    $queryString = Build-QueryString $Query
    if ($queryString) {
        $uri = "$uri?$queryString"
    }

    $statusCode = 0
    $body = ''

    try {
        $resp = Invoke-WebRequest -Method Get -Uri $uri -Headers @{ 'User-Agent' = $script:USER_AGENT }
        $statusCode = [int]$resp.StatusCode
        $body = [string]$resp.Content
    } catch {
        $statusCode = 0

        if ($_.Exception.PSObject.Properties['Response'] -and $null -ne $_.Exception.Response) {
            $respObj = $_.Exception.Response

            if ($respObj.PSObject.Properties['StatusCode']) {
                $statusCode = [int]$respObj.StatusCode
            }

            if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
                $body = [string]$_.ErrorDetails.Message
            } elseif ($respObj.PSObject.Methods.Name -contains 'GetResponseStream') {
                try {
                    $stream = $respObj.GetResponseStream()
                    if ($null -ne $stream) {
                        $reader = [System.IO.StreamReader]::new($stream)
                        $body = $reader.ReadToEnd()
                        $reader.Close()
                    }
                } catch {
                    $body = ''
                }
            } elseif ($respObj.PSObject.Properties['Content']) {
                try {
                    $body = [string]$respObj.Content.ReadAsStringAsync().Result
                } catch {
                    $body = ''
                }
            }
        }

        if ($statusCode -eq 0) {
            Die ((Msg 'api_failed') + ': ' + $_.Exception.Message)
        }
    }

    if ($statusCode -ge 200 -and $statusCode -lt 300) {
        return (Try-ParseJson $body)
    }

    $parsed = Try-ParseJson $body
    $apiError = Get-ApiErrorMessage $parsed

    if ($statusCode -eq 410 -and $apiError -match 'deprecated') {
        Die (Msg 'api_deprecated')
    }

    if ([string]::IsNullOrWhiteSpace($apiError)) {
        if ([string]::IsNullOrWhiteSpace($body)) {
            $apiError = 'Unknown error'
        } else {
            $apiError = $body
        }
    }

    Die ((Msg 'api_failed') + ": HTTP $statusCode $apiError")
}

function Normalize-ToArray {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }

    if ($Value -is [Array]) {
        return $Value
    }

    if ($Value.PSObject.Properties['list']) {
        $list = $Value.list
        if ($list -is [Array]) {
            return $list
        }

        if ($null -ne $list) {
            return @($list)
        }
    }

    return @($Value)
}

function Search-TitlesV1 {
    param([string]$Query)

    Invoke-ApiRequest -Endpoint 'app/search/releases' -Query @{
        query   = $Query
        include = 'id,name,year,episodes_total,type,season,alias'
    }
}

function Search-TitlesV3 {
    param([string]$Query)

    Invoke-ApiRequest -Endpoint 'title/search' -Query @{
        search = $Query
        limit  = '30'
        filter = 'id,names,type,season,player.episodes,episodes_total'
    }
}

function Search-Titles {
    param([string]$Query)

    switch ($script:API_MODE) {
        'v1' { return (Search-TitlesV1 -Query $Query) }
        'v3' { return (Search-TitlesV3 -Query $Query) }
        default { Die "Unsupported API mode: $($script:API_MODE)" }
    }
}

function Filter-SearchResults {
    param(
        $Results,
        [string]$Query
    )

    $items = Normalize-ToArray $Results
    $tokens = [regex]::Split($Query, '[^0-9A-Za-zА-Яа-яЁё]+') | Where-Object { $_.Length -gt 1 }

    if ($tokens.Count -eq 0) {
        return $items
    }

    $filtered = foreach ($item in $items) {
        $fields = @(
            $item.name.main,
            $item.name.english,
            $item.name.alternative,
            $item.names.ru,
            $item.names.en,
            $item.names.alternative,
            $item.alias
        ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

        $haystack = $fields -join ' '
        $ok = $true
        foreach ($token in $tokens) {
            if ($haystack -notmatch [Regex]::Escape($token)) {
                $ok = $false
                break
            }
        }

        if ($ok) {
            $item
        }
    }

    return @($filtered)
}

function Format-SearchMenuV1 {
    param($Results)

    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($item in (Normalize-ToArray $Results)) {
        $id = $item.id
        $ru = if ($item.name.main) { $item.name.main } else { '' }
        $en = if ($item.name.english) { $item.name.english } else { '' }
        $year = if ($item.year) { $item.year } else { '?' }
        $type = if ($item.type.value) { $item.type.value } else { '?' }
        $eps = if ($item.episodes_total) { $item.episodes_total } else { '?' }
        $lines.Add("[$id] $ru / $en | $type | $year | eps: $eps")
    }
    return $lines.ToArray()
}

function Format-SearchMenuV3 {
    param($Results)

    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($item in (Normalize-ToArray $Results)) {
        $id = $item.id
        $ru = if ($item.names.ru) { $item.names.ru } elseif ($item.names.en) { $item.names.en } else { '' }
        $en = if ($item.names.en) { $item.names.en } else { '' }
        $year = if ($item.season.year) { $item.season.year } else { '?' }

        $type = '?'
        if ($item.type.string) {
            $type = $item.type.string
        } elseif ($item.type.full_string) {
            $type = $item.type.full_string
        }

        $eps = '?'
        if ($item.player.episodes.string) {
            $eps = $item.player.episodes.string
        } elseif ($item.player.episodes.last) {
            $eps = $item.player.episodes.last
        } elseif ($item.episodes_total) {
            $eps = $item.episodes_total
        } elseif ($item.type.episodes) {
            $eps = $item.type.episodes
        }

        $lines.Add("[$id] $ru / $en | $type | $year | eps: $eps")
    }
    return $lines.ToArray()
}

function Format-SearchMenu {
    param($Results)

    switch ($script:API_MODE) {
        'v1' { return (Format-SearchMenuV1 -Results $Results) }
        'v3' { return (Format-SearchMenuV3 -Results $Results) }
        default { return @() }
    }
}

function Extract-TitleId {
    param([string]$Line)
    $m = [Regex]::Match($Line, '^\[(\d+)\]')
    if ($m.Success) {
        return $m.Groups[1].Value
    }
    return ''
}

function Fetch-TitleV1 {
    param([string]$Id)

    Invoke-ApiRequest -Endpoint "anime/releases/$Id" -Query @{
        include = 'id,name,episodes_total,episodes.ordinal,episodes.hls_360,episodes.hls_480,episodes.hls_720,episodes.hls_1080'
    }
}

function Fetch-TitleV3 {
    param([string]$Id)

    Invoke-ApiRequest -Endpoint 'title' -Query @{
        id     = $Id
        filter = 'id,names,player,type,season,episodes_total'
    }
}

function Fetch-Title {
    param([string]$Id)

    switch ($script:API_MODE) {
        'v1' { return (Fetch-TitleV1 -Id $Id) }
        'v3' { return (Fetch-TitleV3 -Id $Id) }
        default { Die "Unsupported API mode: $($script:API_MODE)" }
    }
}

function Get-TitleNameV1 {
    param($TitleJson)

    if ($TitleJson.name.main) { return [string]$TitleJson.name.main }
    if ($TitleJson.name.english) { return [string]$TitleJson.name.english }
    return 'Unknown'
}

function Get-TitleNameV3 {
    param($TitleJson)

    if ($TitleJson.names.ru) { return [string]$TitleJson.names.ru }
    if ($TitleJson.names.en) { return [string]$TitleJson.names.en }
    return 'Unknown'
}

function Get-TitleName {
    param($TitleJson)

    switch ($script:API_MODE) {
        'v1' { return (Get-TitleNameV1 -TitleJson $TitleJson) }
        'v3' { return (Get-TitleNameV3 -TitleJson $TitleJson) }
        default { return 'Unknown' }
    }
}

function Get-EpisodesV1 {
    param($TitleJson)

    $episodes = [System.Collections.Generic.List[string]]::new()
    foreach ($ep in $TitleJson.episodes) {
        if ($null -ne $ep.ordinal) {
            $episodes.Add([string]$ep.ordinal)
        }
    }

    return @($episodes.ToArray() | Sort-Object { [int]$_ } -Unique)
}

function Get-EpisodesV3 {
    param($TitleJson)

    $episodes = [System.Collections.Generic.HashSet[string]]::new()
    $list = $TitleJson.player.list

    if ($null -eq $list) {
        return @()
    }

    if ($list -is [Array]) {
        foreach ($item in $list) {
            if ($null -ne $item.episode) {
                [void]$episodes.Add([string]$item.episode)
            }
        }
    } else {
        foreach ($prop in $list.PSObject.Properties) {
            $item = $prop.Value
            if ($null -ne $item -and $item.PSObject.Properties['episode'] -and $null -ne $item.episode) {
                [void]$episodes.Add([string]$item.episode)
            } elseif ($prop.Name -match '^\d+$') {
                [void]$episodes.Add($prop.Name)
            }
        }
    }

    return @($episodes | Sort-Object { [int]$_ } -Unique)
}

function Get-Episodes {
    param($TitleJson)

    switch ($script:API_MODE) {
        'v1' { return (Get-EpisodesV1 -TitleJson $TitleJson) }
        'v3' { return (Get-EpisodesV3 -TitleJson $TitleJson) }
        default { return @() }
    }
}

function Sanitize-Filename {
    param([string]$Name)

    if ([string]::IsNullOrWhiteSpace($Name)) {
        return ''
    }

    $safe = [Regex]::Replace($Name, '[\\/:*?"<>|]+', '_')
    $safe = [Regex]::Replace($safe, '\s+', '_')
    $safe = [Regex]::Replace($safe, '_+', '_')
    $safe = $safe.Trim('_')

    return $safe
}

function Normalize-Url {
    param(
        [string]$Url,
        [string]$Host
    )

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return ''
    }

    if ($Url -match '^https?://') {
        return $Url
    }

    if ($Url.StartsWith('//')) {
        return "https:$Url"
    }

    if ([string]::IsNullOrWhiteSpace($Host)) {
        return $Url
    }

    $hostPrefix = if ($Host -match '^https?://') { $Host.TrimEnd('/') } else { "https://$($Host.TrimEnd('/'))" }
    if ($Url.StartsWith('/')) {
        return "$hostPrefix$Url"
    }

    return "$hostPrefix/$Url"
}

function Pick-FromQualityObject {
    param(
        $Object,
        [string]$Desired
    )

    if ($null -eq $Object) {
        return ''
    }

    if ($Object -is [string]) {
        return [string]$Object
    }

    $map = @{}
    foreach ($prop in $Object.PSObject.Properties) {
        if ($null -ne $prop.Value) {
            $map[(Lower $prop.Name)] = [string]$prop.Value
        }
    }

    if ($map.Count -eq 0) {
        return ''
    }

    $keys = @()
    switch ($Desired) {
        '1080p' { $keys = @('1080', 'hls_1080', 'fhd', 'fullhd') }
        '720p' { $keys = @('720', 'hls_720', 'hd') }
        '480p' { $keys = @('480', 'hls_480', 'sd') }
        '360p' { $keys = @('360', 'hls_360', 'ld', 'low') }
        'best' { $keys = @('1080', 'hls_1080', 'fhd', 'fullhd', '720', 'hls_720', 'hd', '480', 'hls_480', 'sd', '360', 'hls_360', 'ld', 'low') }
        'worst' { $keys = @('360', 'hls_360', 'ld', 'low', '480', 'hls_480', 'sd', '720', 'hls_720', 'hd', '1080', 'hls_1080', 'fhd', 'fullhd') }
    }

    foreach ($key in $keys) {
        $k = Lower $key
        if ($map.ContainsKey($k) -and -not [string]::IsNullOrWhiteSpace($map[$k])) {
            return [string]$map[$k]
        }
    }

    foreach ($value in $map.Values) {
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return [string]$value
        }
    }

    return ''
}

function Stream-UrlV1 {
    param(
        $TitleJson,
        [string]$Episode
    )

    $epJson = $null
    foreach ($ep in $TitleJson.episodes) {
        if ([string]$ep.ordinal -eq $Episode) {
            $epJson = $ep
            break
        }
    }

    if ($null -eq $epJson) {
        return ''
    }

    if ((Lower $script:STREAM_TYPE) -eq 'sub' -and -not $script:SUBTITLE_FALLBACK_WARNED) {
        Warn (Msg 'sub_fallback')
        $script:SUBTITLE_FALLBACK_WARNED = $true
    }

    switch ($script:QUALITY) {
        '1080p' { $url = if ($epJson.hls_1080) { $epJson.hls_1080 } elseif ($epJson.hls_720) { $epJson.hls_720 } elseif ($epJson.hls_480) { $epJson.hls_480 } else { $epJson.hls_360 } }
        '720p' { $url = if ($epJson.hls_720) { $epJson.hls_720 } elseif ($epJson.hls_1080) { $epJson.hls_1080 } elseif ($epJson.hls_480) { $epJson.hls_480 } else { $epJson.hls_360 } }
        '480p' { $url = if ($epJson.hls_480) { $epJson.hls_480 } elseif ($epJson.hls_360) { $epJson.hls_360 } elseif ($epJson.hls_720) { $epJson.hls_720 } else { $epJson.hls_1080 } }
        '360p' { $url = if ($epJson.hls_360) { $epJson.hls_360 } elseif ($epJson.hls_480) { $epJson.hls_480 } elseif ($epJson.hls_720) { $epJson.hls_720 } else { $epJson.hls_1080 } }
        'worst' { $url = if ($epJson.hls_360) { $epJson.hls_360 } elseif ($epJson.hls_480) { $epJson.hls_480 } elseif ($epJson.hls_720) { $epJson.hls_720 } else { $epJson.hls_1080 } }
        default { $url = if ($epJson.hls_1080) { $epJson.hls_1080 } elseif ($epJson.hls_720) { $epJson.hls_720 } elseif ($epJson.hls_480) { $epJson.hls_480 } else { $epJson.hls_360 } }
    }

    if ($null -eq $url) { return '' }
    return [string]$url
}

function Resolve-V3EpisodeNode {
    param(
        $PlayerList,
        [string]$Episode
    )

    if ($null -eq $PlayerList) {
        return $null
    }

    if ($PlayerList -is [Array]) {
        foreach ($item in $PlayerList) {
            if ([string]$item.episode -eq $Episode) {
                return $item
            }
        }
        return $null
    }

    if ($PlayerList.PSObject.Properties[$Episode]) {
        return $PlayerList.PSObject.Properties[$Episode].Value
    }

    foreach ($prop in $PlayerList.PSObject.Properties) {
        $value = $prop.Value
        if ($null -ne $value -and $value.PSObject.Properties['episode'] -and [string]$value.episode -eq $Episode) {
            return $value
        }
    }

    return $null
}

function Stream-UrlV3 {
    param(
        $TitleJson,
        [string]$Episode
    )

    $host = ''
    if ($TitleJson.player.host.hls) {
        $host = [string]$TitleJson.player.host.hls
    } elseif ($TitleJson.player.host) {
        $host = [string]$TitleJson.player.host
    } elseif ($TitleJson.host.hls) {
        $host = [string]$TitleJson.host.hls
    } elseif ($TitleJson.host) {
        $host = [string]$TitleJson.host
    }

    $epJson = Resolve-V3EpisodeNode -PlayerList $TitleJson.player.list -Episode $Episode
    if ($null -eq $epJson) {
        return ''
    }

    $streamNode = $null
    if ((Lower $script:STREAM_TYPE) -eq 'sub') {
        if ($epJson.hls.subtitles) {
            $streamNode = $epJson.hls.subtitles
        } elseif ($epJson.hls.sub) {
            $streamNode = $epJson.hls.sub
        } elseif ($epJson.subtitles) {
            $streamNode = $epJson.subtitles
        }

        if ($null -eq $streamNode) {
            if (-not $script:SUBTITLE_FALLBACK_WARNED) {
                Warn (Msg 'sub_fallback')
                $script:SUBTITLE_FALLBACK_WARNED = $true
            }

            if ($epJson.hls.ru) {
                $streamNode = $epJson.hls.ru
            } elseif ($epJson.hls.dub) {
                $streamNode = $epJson.hls.dub
            } elseif ($epJson.hls) {
                $streamNode = $epJson.hls
            }
        }
    } else {
        if ($epJson.hls.ru) {
            $streamNode = $epJson.hls.ru
        } elseif ($epJson.hls.dub) {
            $streamNode = $epJson.hls.dub
        } elseif ($epJson.hls) {
            $streamNode = $epJson.hls
        }
    }

    if ($null -eq $streamNode) {
        return ''
    }

    if ($streamNode -is [string]) {
        $rawUrl = [string]$streamNode
    } else {
        $rawUrl = Pick-FromQualityObject -Object $streamNode -Desired $script:QUALITY
    }

    if ([string]::IsNullOrWhiteSpace($rawUrl)) {
        return ''
    }

    return (Normalize-Url -Url $rawUrl -Host $host)
}

function Get-StreamUrl {
    param(
        $TitleJson,
        [string]$Episode
    )

    switch ($script:API_MODE) {
        'v1' { return (Stream-UrlV1 -TitleJson $TitleJson -Episode $Episode) }
        'v3' { return (Stream-UrlV3 -TitleJson $TitleJson -Episode $Episode) }
        default { return '' }
    }
}

function Is-Number {
    param([string]$Value)
    return $Value -match '^\d+$'
}

function Build-Range {
    param(
        [int]$Start,
        [int]$End
    )

    $vals = [System.Collections.Generic.List[string]]::new()
    for ($i = $Start; $i -le $End; $i++) {
        $vals.Add([string]$i)
    }

    return $vals.ToArray()
}

function Validate-EpisodeSelection {
    param(
        [string[]]$Selected,
        [string[]]$Available
    )

    $lookup = @{}
    foreach ($ep in $Available) {
        $lookup[[string]$ep] = $true
    }

    foreach ($ep in $Selected) {
        if (-not $lookup.ContainsKey([string]$ep)) {
            Die ((Msg 'episode_unavailable') + ': ' + $ep)
        }
    }
}

function Detect-DefaultPlayer {
    if (-not [string]::IsNullOrWhiteSpace($script:PLAYER)) {
        return $script:PLAYER
    }

    if ($IsWindows) {
        if (Has-Command 'mpv.exe') {
            return 'mpv.exe'
        }
        return 'mpv'
    }

    return 'mpv'
}

function Resolve-Player {
    $preferred = Detect-DefaultPlayer

    if ($script:PLAYER_FORCED) {
        if (-not (Has-Command $preferred)) {
            Die ((Msg 'need_player') + ': ' + $preferred)
        }

        $script:PLAYER = $preferred
        return
    }

    if (Has-Command $preferred) {
        $script:PLAYER = $preferred
        return
    }

    foreach ($fallback in @('mpv.exe', 'vlc.exe', 'mpv', 'vlc', 'iina')) {
        if (Has-Command $fallback) {
            $script:PLAYER = $fallback
            Warn "Using fallback player: $($script:PLAYER)"
            return
        }
    }

    Die (Msg 'need_player')
}

function Play-Episode {
    param(
        [string]$Url,
        [string]$Title,
        [string]$Episode
    )

    $playerLower = Lower $script:PLAYER
    switch ($playerLower) {
        'mpv' {
            & $script:PLAYER $Url "--force-media-title=$Title - $(Msg 'episode_word') $Episode"
            return
        }
        'mpv.exe' {
            & $script:PLAYER $Url "--force-media-title=$Title - $(Msg 'episode_word') $Episode"
            return
        }
        'vlc' {
            & $script:PLAYER $Url
            return
        }
        'vlc.exe' {
            & $script:PLAYER $Url
            return
        }
        'iina' {
            & $script:PLAYER $Url
            return
        }
        default {
            Die ((Msg 'need_player') + ': ' + $script:PLAYER)
        }
    }
}

function Ensure-Downloader {
    if (Has-Command 'aria2c') {
        $script:DOWNLOADER = 'aria2c'
    } elseif (Has-Command 'aria2c.exe') {
        $script:DOWNLOADER = 'aria2c.exe'
    } elseif (Has-Command 'wget.exe') {
        $script:DOWNLOADER = 'wget.exe'
    } elseif (Has-Command 'wget') {
        $script:DOWNLOADER = 'wget'
    } else {
        $script:DOWNLOADER = 'iwr'
    }
}

function Download-Episode {
    param(
        [string]$Url,
        [string]$Title,
        [string]$Episode
    )

    if (-not (Test-Path -LiteralPath $script:DOWNLOAD_DIR -PathType Container)) {
        New-Item -Path $script:DOWNLOAD_DIR -ItemType Directory -Force | Out-Null
    }

    $safeTitle = Sanitize-Filename $Title
    if ([string]::IsNullOrWhiteSpace($safeTitle)) {
        $safeTitle = 'anime'
    }

    $outFile = "{0}_ep{1}_{2}_{3}.m3u8" -f $safeTitle, $Episode, $script:QUALITY, $script:STREAM_TYPE
    $targetPath = Join-Path $script:DOWNLOAD_DIR $outFile

    switch ($script:DOWNLOADER) {
        'aria2c' {
            & aria2c --continue=true --allow-overwrite=true --dir="$($script:DOWNLOAD_DIR)" --out="$outFile" "$Url"
            break
        }
        'aria2c.exe' {
            & aria2c.exe --continue=true --allow-overwrite=true --dir="$($script:DOWNLOAD_DIR)" --out="$outFile" "$Url"
            break
        }
        'wget' {
            & wget -O "$targetPath" "$Url"
            break
        }
        'wget.exe' {
            & wget.exe -O "$targetPath" "$Url"
            break
        }
        default {
            Invoke-WebRequest -Uri $Url -OutFile $targetPath
            break
        }
    }

    Write-Output ((Msg 'download_saved') + ": $targetPath")
}

function Parse-Args {
    param([string[]]$Argv)

    $queryParts = [System.Collections.Generic.List[string]]::new()

    for ($i = 0; $i -lt $Argv.Count; $i++) {
        $arg = $Argv[$i]

        switch ($arg) {
            '-h' {
                Print-Help
                exit 0
            }
            '--help' {
                Print-Help
                exit 0
            }
            '-v' {
                Write-Output "ani-cli-ru v$($script:VERSION)"
                exit 0
            }
            '--version' {
                Write-Output "ani-cli-ru v$($script:VERSION)"
                exit 0
            }
            '-q' {
                if ($i + 1 -ge $Argv.Count) {
                    Die (Msg 'invalid_quality')
                }
                $i++
                $script:QUALITY = $Argv[$i]
            }
            '--quality' {
                if ($i + 1 -ge $Argv.Count) {
                    Die (Msg 'invalid_quality')
                }
                $i++
                $script:QUALITY = $Argv[$i]
            }
            '-d' {
                $script:DOWNLOAD_MODE = $true
            }
            '--download' {
                $script:DOWNLOAD_MODE = $true
            }
            '-e' {
                if ($i + 1 -ge $Argv.Count) {
                    Die (Msg 'invalid_episode')
                }
                $i++
                $script:EPISODE_ARG = $Argv[$i]
            }
            '--episode' {
                if ($i + 1 -ge $Argv.Count) {
                    Die (Msg 'invalid_episode')
                }
                $i++
                $script:EPISODE_ARG = $Argv[$i]
            }
            '-r' {
                if ($i + 1 -ge $Argv.Count) {
                    Die (Msg 'invalid_range')
                }
                $i++
                $script:RANGE_ARG = $Argv[$i]
            }
            '--range' {
                if ($i + 1 -ge $Argv.Count) {
                    Die (Msg 'invalid_range')
                }
                $i++
                $script:RANGE_ARG = $Argv[$i]
            }
            '-l' {
                $script:SHOW_LOG = $true
            }
            '--logview' {
                $script:SHOW_LOG = $true
            }
            '-D' {
                $script:DELETE_LOG = $true
            }
            '--delete' {
                $script:DELETE_LOG = $true
            }
            '--lang' {
                if ($i + 1 -ge $Argv.Count) {
                    Die (Msg 'invalid_lang')
                }
                $i++
                $script:LANGUAGE = $Argv[$i]
            }
            '--sub' {
                $script:STREAM_TYPE = 'sub'
            }
            '--vlc' {
                $script:PLAYER = 'vlc.exe'
                $script:PLAYER_FORCED = $true
            }
            '--rofi' {
                Warn 'rofi is not supported on Windows PowerShell. Using built-in selector/fzf.'
            }
            '--' {
                for ($j = $i + 1; $j -lt $Argv.Count; $j++) {
                    $queryParts.Add($Argv[$j])
                }
                $i = $Argv.Count
                continue
            }
            default {
                if ($arg.StartsWith('-')) {
                    Die ((Msg 'unknown_option') + ': ' + $arg)
                }
                $queryParts.Add($arg)
            }
        }
    }

    $script:QUERY = ($queryParts -join ' ')
}

function Main {
    param([string[]]$Argv)

    Parse-Args -Argv $Argv

    $script:LANGUAGE = Normalize-Lang $script:LANGUAGE
    if ([string]::IsNullOrWhiteSpace($script:LANGUAGE)) {
        Die (Msg 'invalid_lang')
    }

    $script:QUALITY = Normalize-Quality $script:QUALITY
    if ([string]::IsNullOrWhiteSpace($script:QUALITY)) {
        Die (Msg 'invalid_quality')
    }

    $script:STREAM_TYPE = Lower $script:STREAM_TYPE
    if ($script:STREAM_TYPE -notin @('dub', 'sub')) {
        $script:STREAM_TYPE = 'dub'
    }

    $script:MENU_BACKEND = Lower $script:MENU_BACKEND

    Detect-ApiMode

    if ($script:SHOW_LOG) {
        Show-History
        exit 0
    }

    if ($script:DELETE_LOG) {
        Clear-History
        exit 0
    }

    if ($script:DOWNLOAD_MODE) {
        Ensure-Downloader
    } else {
        Resolve-Player
    }

    $script:QUERY = Trim-Value $script:QUERY
    if ([string]::IsNullOrWhiteSpace($script:QUERY)) {
        $script:QUERY = Trim-Value (Read-Host (Msg 'prompt_query'))
    }

    if ([string]::IsNullOrWhiteSpace($script:QUERY)) {
        Die (Msg 'choose_query')
    }

    $rawResults = Search-Titles -Query $script:QUERY
    $results = Filter-SearchResults -Results $rawResults -Query $script:QUERY
    if ($results.Count -le 0) {
        Die (Msg 'no_results')
    }

    $menuLines = Format-SearchMenu -Results $results
    $selectedLine = Select-Line -Lines $menuLines -Prompt (Msg 'select_title') -Hint $script:QUERY
    if ([string]::IsNullOrWhiteSpace($selectedLine)) {
        exit 1
    }

    $titleId = Extract-TitleId $selectedLine
    if ([string]::IsNullOrWhiteSpace($titleId)) {
        Die 'Failed to parse selected title'
    }

    $titleJson = Fetch-Title -Id $titleId
    $titleName = Get-TitleName -TitleJson $titleJson

    $availableEpisodes = Get-Episodes -TitleJson $titleJson
    if ($availableEpisodes.Count -eq 0) {
        Die (Msg 'no_results')
    }

    if (-not [string]::IsNullOrWhiteSpace($script:EPISODE_ARG) -and -not [string]::IsNullOrWhiteSpace($script:RANGE_ARG)) {
        Die 'Use only one of --episode or --range'
    }

    if (-not [string]::IsNullOrWhiteSpace($script:EPISODE_ARG)) {
        $selectedEpisodes = @($script:EPISODE_ARG)
    } elseif (-not [string]::IsNullOrWhiteSpace($script:RANGE_ARG)) {
        if ($script:RANGE_ARG -notmatch '^\d+-\d+$') {
            Die (Msg 'invalid_range')
        }

        $parts = $script:RANGE_ARG -split '-', 2
        $start = [int]$parts[0]
        $end = [int]$parts[1]

        if ($start -gt $end) {
            Die (Msg 'invalid_range')
        }

        $selectedEpisodes = Build-Range -Start $start -End $end
    } else {
        $epMenu = foreach ($ep in $availableEpisodes) {
            "[{0}] {1} {2}" -f $ep, (Msg 'episode_word'), $ep
        }

        $selectedEpLine = Select-Line -Lines $epMenu -Prompt (Msg 'select_episode')
        if ([string]::IsNullOrWhiteSpace($selectedEpLine)) {
            exit 1
        }

        $m = [Regex]::Match($selectedEpLine, '^\[([^\]]+)\]')
        if (-not $m.Success) {
            Die (Msg 'invalid_episode')
        }

        $selectedEpisodes = @($m.Groups[1].Value)
    }

    $selectedEpisodes = @($selectedEpisodes | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($selectedEpisodes.Count -eq 0) {
        Die (Msg 'invalid_episode')
    }

    Validate-EpisodeSelection -Selected $selectedEpisodes -Available $availableEpisodes

    foreach ($ep in $selectedEpisodes) {
        $streamUrl = Get-StreamUrl -TitleJson $titleJson -Episode $ep
        if ([string]::IsNullOrWhiteSpace($streamUrl)) {
            Die ((Msg 'stream_missing') + ': ' + $ep)
        }

        if ($script:DOWNLOAD_MODE) {
            Write-Output ("{0}: {1} - {2} {3}" -f (Msg 'downloading'), $titleName, (Msg 'episode_word'), $ep)
            Download-Episode -Url $streamUrl -Title $titleName -Episode $ep
        } else {
            Write-Output ("{0}: {1} - {2} {3}" -f (Msg 'playing'), $titleName, (Msg 'episode_word'), $ep)
            Play-Episode -Url $streamUrl -Title $titleName -Episode $ep
        }

        Append-History -TitleId $titleId -TitleName $titleName -Episode $ep -Quality $script:QUALITY -StreamType $script:STREAM_TYPE
    }
}

Main -Argv $args
