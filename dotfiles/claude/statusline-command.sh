#!/bin/bash
input=$(cat)

RESET="\033[0m"
BOLD="\033[1m"
rgb() { printf "\033[38;2;%d;%d;%dm" "$1" "$2" "$3"; }
DIMGRAY=$(rgb 120 120 120)
EMPTYGRAY=$(rgb 60 60 60)
BOLDYELLOW="${BOLD}$(rgb 230 200 30)"
BOLDCYAN="${BOLD}$(rgb 0 200 200)"
BOLDMAGENTA="${BOLD}$(rgb 220 60 220)"
BOLDBRIGHTCYAN="${BOLD}$(rgb 0 255 255)"
BRIGHTGREEN=$(rgb 60 220 60)
BRIGHTRED=$(rgb 220 60 60)
GREEN=$(rgb 0 200 80)
YELLOW=$(rgb 220 200 0)
RED=$(rgb 220 40 20)
SEP="${DIMGRAY}│${RESET}"

# green(0,200,80) -> yellow(220,200,0) -> red(220,40,20) gradient by pct 0-100
gradient_color() {
  local pct=$1
  if [ "$pct" -le 50 ]; then
    local t=$pct
    r=$((0 + t * 220 / 50)); g=$((200 + t * (200 - 200) / 50)); g=200; b=$((80 - t * 80 / 50))
  else
    local t=$((pct - 50))
    r=220; g=$((200 - t * 160 / 50)); b=$((0 + t * 20 / 50))
  fi
  echo "$r $g $b"
}

# 10-cell bar for a given pct (0-100), colored via gradient_color
render_bar() {
  local pct=$1
  local filled=$(( (pct * 10 + 50) / 100 ))
  [ "$filled" -gt 10 ] && filled=10
  [ "$filled" -lt 0 ] && filled=0
  local bar=""
  read cr cg cb <<< "$(gradient_color "$pct")"
  local fillcolor
  fillcolor=$(rgb "$cr" "$cg" "$cb")
  for i in $(seq 1 10); do
    if [ "$i" -le "$filled" ]; then
      bar="${bar}${fillcolor}█${RESET}"
    else
      bar="${bar}${EMPTYGRAY}░${RESET}"
    fi
  done
  echo "$bar"
}

# format seconds-until epoch into "XhYYm" (5h window) or "Xd" (weekly window)
format_renew() {
  local resets_at=$1
  local now=$(date +%s)
  local diff=$(( resets_at - now ))
  if [ "$diff" -lt 0 ]; then diff=0; fi
  local hours=$(( diff / 3600 ))
  local mins=$(( (diff % 3600) / 60 ))
  printf "%dh%02dm" "$hours" "$mins"
}

format_renew_days() {
  local resets_at=$1
  local now=$(date +%s)
  local diff=$(( resets_at - now ))
  if [ "$diff" -lt 0 ]; then diff=0; fi
  local days=$(( (diff + 86399) / 86400 ))
  printf "%dd" "$days"
}

segments=()

# --- 1. Model ---
model=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
segments+=("$(printf "${BOLDBRIGHTCYAN}%s${RESET}" "$model")")

# --- 2. Context usage (numeric only) ---
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
if [ -n "$used_pct" ]; then
  pct_int=$(printf "%.0f" "$used_pct")
  if [ "$pct_int" -ge 70 ]; then ctxcolor="$RED"; elif [ "$pct_int" -ge 40 ]; then ctxcolor="$YELLOW"; else ctxcolor="$GREEN"; fi
  segments+=("$(printf "${ctxcolor}%d%%${RESET}" "$pct_int")")
fi

# --- 3. 5h session limit ---
five_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
five_resets=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
if [ -n "$five_pct" ]; then
  pct_int=$(printf "%.0f" "$five_pct")
  read cr cg cb <<< "$(gradient_color "$pct_int")"
  pctcolor=$(rgb "$cr" "$cg" "$cb")
  renew=""
  [ -n "$five_resets" ] && renew="·$(format_renew "$five_resets")"
  segments+=("$(printf "5h %s ${pctcolor}%d%%${RESET}%s" "$(render_bar "$pct_int")" "$pct_int" "$renew")")
fi

# --- 4. Weekly session limit ---
week_pct=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
week_resets=$(echo "$input" | jq -r '.rate_limits.seven_day.resets_at // empty')
if [ -n "$week_pct" ]; then
  pct_int=$(printf "%.0f" "$week_pct")
  read cr cg cb <<< "$(gradient_color "$pct_int")"
  pctcolor=$(rgb "$cr" "$cg" "$cb")
  renew=""
  [ -n "$week_resets" ] && renew="·$(format_renew_days "$week_resets")"
  segments+=("$(printf "7d %s ${pctcolor}%d%%${RESET}%s" "$(render_bar "$pct_int")" "$pct_int" "$renew")")
fi

# --- Join with dim pipe separators ---
result=""
for i in "${!segments[@]}"; do
  if [ "$i" -eq 0 ]; then
    result="${segments[$i]}"
  else
    result="${result} ${SEP} ${segments[$i]}"
  fi
done

printf "%b" "$result"
