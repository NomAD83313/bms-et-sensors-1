#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/compose-common.sh"

bms_cd_project

ENV_FILE="${ENV_FILE:-${PROJECT_ROOT}/.env}"
load_env() {
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
  fi
}

load_env

REALTEK_BLE_USB_VID="0bda"
REALTEK_BLE_USB_PID="8771"
REALTEK_BLE_ADDRESS="8C:88:2B:24:32:8F"

configure_matter_server_backend() {
  local backend="${MATTER_SERVER_BACKEND:-matterjs}"

  case "${backend}" in
    matterjs)
      export MATTER_SERVER_BACKEND="matterjs"
      export MATTER_SERVER_IMAGE="${MATTER_SERVER_IMAGE:-ghcr.io/matter-js/matterjs-server:stable}"
      export MATTER_SERVER_DATA_DIR="${MATTER_SERVER_DATA_DIR:-./runtime/matterjs-server}"
      export MATTER_SERVER_USER="${MATTER_SERVER_USER:-0:0}"
      export MATTER_SERVER_PRODUCTION_MODE="${MATTER_SERVER_PRODUCTION_MODE:-true}"
      ;;
    *)
      echo "ERROR: Unsupported MATTER_SERVER_BACKEND=${backend}. This lab branch supports matterjs only." >&2
      exit 1
      ;;
  esac
}

detect_usb_ble_adapter_index() {
  local hci_path=""
  local hci_name=""
  local sys_path=""
  local probe_path=""
  local vid=""
  local pid=""
  local idx=""
  local address=""
  local matches=()

  shopt -s nullglob
  for hci_path in /sys/class/bluetooth/hci*; do
    hci_name="$(basename "${hci_path}")"
    sys_path="$(readlink -f "${hci_path}/device" 2>/dev/null || true)"
    if [[ -z "${sys_path}" ]]; then
      continue
    fi

    probe_path="${sys_path}"
    vid=""
    pid=""
    while [[ "${probe_path}" != "/" ]]; do
      if [[ -f "${probe_path}/idVendor" && -f "${probe_path}/idProduct" ]]; then
        vid="$(tr '[:upper:]' '[:lower:]' < "${probe_path}/idVendor" 2>/dev/null || true)"
        pid="$(tr '[:upper:]' '[:lower:]' < "${probe_path}/idProduct" 2>/dev/null || true)"
        break
      fi
      probe_path="$(dirname "${probe_path}")"
    done

    if [[ "${vid,,}" == "${REALTEK_BLE_USB_VID}" && "${pid,,}" == "${REALTEK_BLE_USB_PID}" ]]; then
      idx="${hci_name#hci}"
      if ! [[ "${idx}" =~ ^[0-9]+$ ]]; then
        continue
      fi
      address="$(hciconfig "${hci_name}" 2>/dev/null | awk '/BD Address:/ {print toupper($3); exit}')"
      if [[ "${address}" != "${REALTEK_BLE_ADDRESS}" ]]; then
        continue
      fi
      matches+=("${idx}|${address}|${sys_path}")
    fi
  done
  shopt -u nullglob

  if [[ "${#matches[@]}" -eq 1 ]]; then
    echo "${matches[0]}"
    return 0
  fi
  if [[ "${#matches[@]}" -gt 1 ]]; then
    echo "ERROR: Multiple matching Realtek BLE adapters found." >&2
    printf 'ERROR: matches: %s\n' "${matches[@]}" >&2
  fi
  return 1
}

configure_matter_server_backend

if detected_adapter="$(detect_usb_ble_adapter_index)"; then
  IFS="|" read -r detected_idx detected_address detected_sys_path <<< "${detected_adapter}"
  export MATTER_REALTEK_BLUETOOTH_ADAPTER="${detected_idx}"
  echo ">>> Using Realtek BLE adapter hci${MATTER_REALTEK_BLUETOOTH_ADAPTER} (${detected_address:-unknown address}, VID:PID ${REALTEK_BLE_USB_VID}:${REALTEK_BLE_USB_PID})"
  echo ">>> Adapter sysfs path: ${detected_sys_path}"
else
  echo "ERROR: Required Realtek BLE adapter was not detected." >&2
  echo "ERROR: Expected VID:PID ${REALTEK_BLE_USB_VID}:${REALTEK_BLE_USB_PID}, Bluetooth address ${REALTEK_BLE_ADDRESS}." >&2
  echo "ERROR: Internal BLE fallback is disabled by project architecture." >&2
  echo "ERROR: MediaTek BLE is intentionally not allowed for Matter commissioning." >&2
  echo "ERROR: Check the Realtek USB dongle connection." >&2
  exit 1
fi

echo ">>> Starting Matter profile services with ${MATTER_SERVER_BACKEND} backend..."
"${COMPOSE[@]}" --profile matter up -d --force-recreate matter-server matter-collector
bms_verify_services_created matter-server matter-collector

echo ">>> Done (matter-server + matter-collector)."
