#!/usr/bin/env python3
"""
Mac용 실행 파일 빌드 스크립트
"""
import PyInstaller.__main__
import shutil
from pathlib import Path

# 이전 빌드 정리
for folder in ['build', 'dist']:
    if Path(folder).exists():
        shutil.rmtree(folder)
        print(f"기존 {folder} 폴더 삭제됨")

print("Mac용 앱 빌드 시작...")

# 빌드 인자 준비
args = [
    'run_streamlit.py',
    '--name=송장자동화',
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

PyInstaller.__main__.run(args)

print("\n" + "="*50)
print("빌드 완료!")
print("="*50)
print(f"실행 파일 위치: {Path('dist').absolute()}")
print("\n실행 방법:")
print("  1. dist 폴더를 열어주세요")
print("  2. '송장자동화.app' 파일을 더블클릭하세요")
print("\n다른 Mac 사용자에게 전달:")
print("  - dist/송장자동화.app 폴더 전체를 압축해서 전달하세요")
print("  - 받는 사람은 압축 풀고 .app 파일을 더블클릭하면 됩니다")
print("  - Python 설치 없이 바로 실행 가능합니다!")
print(f"\n앱 크기: {sum(f.stat().st_size for f in Path('dist/송장자동화.app').rglob('*') if f.is_file()) / 1024 / 1024:.1f} MB")
