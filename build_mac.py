#!/usr/bin/env python3
"""
Mac용 실행 파일 빌드 스크립트
사용법:
  python build_mac.py           # 기본 빌드 (macOS 15.1 타겟)
  python build_mac.py 15.1      # macOS 15.1 타겟
  python build_mac.py 15.5      # macOS 15.5 타겟
  python build_mac.py all       # 모든 버전 빌드 (15.1, 15.5)
"""
import PyInstaller.__main__
import shutil
import sys
import os
from pathlib import Path

# 타겟 버전 설정
TARGET_VERSIONS = {
    '15.1': '15.1',
    '15.5': '15.5',
}

def build_for_version(target_version):
    """특정 macOS 버전을 타겟으로 빌드"""
    print(f"\n{'='*60}")
    print(f"macOS {target_version} 타겟으로 빌드 시작...")
    print(f"{'='*60}\n")

    # macOS 타겟 버전 환경 변수 설정
    os.environ['MACOSX_DEPLOYMENT_TARGET'] = target_version
    print(f"✓ MACOSX_DEPLOYMENT_TARGET={target_version} 설정됨")

    # 버전별 출력 폴더명
    version_suffix = target_version.replace('.', '_')
    app_name = f'storeauto_macos{version_suffix}'

    # 이전 빌드 정리
    for folder in ['build', 'dist']:
        if Path(folder).exists():
            shutil.rmtree(folder)
            print(f"✓ 기존 {folder} 폴더 삭제됨")

    # 빌드 인자 준비
    args = [
        'run_streamlit.py',
        f'--name={app_name}',
        '--windowed',  # Mac 앱 번들 생성
        '--onedir',  # 디렉토리 모드 (더 안정적)
        '--add-data=app.py:.',
        '--hidden-import=streamlit',
        '--hidden-import=streamlit.web',
        '--hidden-import=streamlit.web.cli',
        '--hidden-import=pandas',
        '--hidden-import=openpyxl',
        '--collect-all=streamlit',
        '--collect-all=altair',
        '--noconfirm',
        '--clean',
    ]

    # output 폴더가 있으면 포함
    if Path('output').exists():
        args.append('--add-data=output:output')
        print("✓ output 폴더 포함됨")

    # PyInstaller 실행
    PyInstaller.__main__.run(args)

    # 빌드 결과를 버전별 폴더로 이동
    dist_path = Path('dist')
    version_dist = Path(f'dist_macos{version_suffix}')

    if dist_path.exists():
        if version_dist.exists():
            shutil.rmtree(version_dist)
        dist_path.rename(version_dist)
        print(f"✓ 빌드 결과를 {version_dist} 폴더로 이동")

    print(f"\n{'='*60}")
    print(f"macOS {target_version} 타겟 빌드 완료!")
    print(f"{'='*60}")
    print(f"실행 파일 위치: {version_dist.absolute()}")
    print(f"앱 이름: {app_name}.app")

    # 앱 크기 계산
    app_path = version_dist / f'{app_name}.app'
    if app_path.exists():
        size_mb = sum(f.stat().st_size for f in app_path.rglob('*') if f.is_file()) / 1024 / 1024
        print(f"앱 크기: {size_mb:.1f} MB")

    return version_dist

# 커맨드 라인 인자 처리
if len(sys.argv) > 1:
    target = sys.argv[1]
else:
    target = '15.1'  # 기본값: 가장 낮은 버전 (호환성 최대화)

print("="*60)
print("Mac용 앱 빌드 스크립트")
print("="*60)

if target == 'all':
    # 모든 버전 빌드
    print("\n모든 버전 빌드를 시작합니다...")
    built_versions = []
    for version in TARGET_VERSIONS.values():
        try:
            version_dist = build_for_version(version)
            built_versions.append((version, version_dist))
        except Exception as e:
            print(f"\n⚠ macOS {version} 빌드 실패: {e}")

    # 최종 결과 출력
    print("\n" + "="*60)
    print("전체 빌드 완료!")
    print("="*60)
    for version, dist_path in built_versions:
        print(f"✓ macOS {version}: {dist_path}")

elif target in TARGET_VERSIONS:
    # 특정 버전 빌드
    build_for_version(TARGET_VERSIONS[target])

else:
    # 잘못된 버전
    print(f"\n⚠ 잘못된 타겟 버전: {target}")
    print("\n사용 가능한 버전:")
    for version in TARGET_VERSIONS.keys():
        print(f"  - {version}")
    print("  - all (모든 버전)")
    sys.exit(1)

print("\n" + "="*60)
print("사용 방법:")
print("="*60)
print("1. dist_macos버전 폴더를 열어주세요")
print("2. '.app' 파일을 더블클릭하세요")
print("\n다른 Mac 사용자에게 전달:")
print("  - dist_macos버전 폴더 전체를 압축해서 전달하세요")
print("  - macOS 15.1 사용자는 15.1 버전을")
print("  - macOS 15.5 사용자는 15.5 버전을 사용하세요")
print("  - Python 설치 없이 바로 실행 가능합니다!")
