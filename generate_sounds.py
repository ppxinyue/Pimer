import numpy as np
from scipy.io import wavfile
import os
from pathlib import Path

# 确保sounds目录存在
sounds_dir = Path('sounds')
sounds_dir.mkdir(exist_ok=True)

def generate_sine_wave(freq, duration, sample_rate=44100):
    """生成正弦波"""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = np.sin(2 * np.pi * freq * t)
    return wave

def generate_bingo_sound():
    """生成bingo音效 - 上升的音阶和欢快的结尾"""
    sample_rate = 44100
    total_duration = 0
    waves = []
    
    # 上升的音阶
    for freq in [523.25, 587.33, 659.25, 698.46, 783.99, 880.00]:  # C5, D5, E5, F5, G5, A5
        wave = generate_sine_wave(freq, 0.15, sample_rate)
        # 应用淡入淡出效果
        fade_samples = int(0.05 * sample_rate)
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        wave[:fade_samples] *= fade_in
        wave[-fade_samples:] *= fade_out
        waves.append(wave)
        total_duration += 0.15
    
    # 欢快的结尾和弦
    chord_freqs = [523.25, 659.25, 783.99]  # C5, E5, G5
    chord_duration = 0.3
    chord_waves = [generate_sine_wave(freq, chord_duration, sample_rate) for freq in chord_freqs]
    chord_wave = sum(chord_waves) / len(chord_freqs)
    # 应用淡入淡出效果
    fade_samples = int(0.1 * sample_rate)
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    chord_wave[:fade_samples] *= fade_in
    chord_wave[-fade_samples:] *= fade_out
    waves.append(chord_wave)
    
    # 合并所有波形
    combined_wave = np.concatenate(waves)
    
    # 归一化到 [-1, 1] 范围
    combined_wave = combined_wave / np.max(np.abs(combined_wave))
    
    # 转换为16位整数
    combined_wave = (combined_wave * 32767).astype(np.int16)
    
    # 保存为WAV文件
    wavfile.write(sounds_dir / 'bingo.wav', sample_rate, combined_wave)
    print(f"已生成bingo音效: {sounds_dir / 'bingo.wav'}")

def generate_achievement_sound():
    """生成achievement音效 - 短促的上升音阶"""
    sample_rate = 44100
    total_duration = 0
    waves = []
    
    # 短促的上升音阶
    for freq in [440.00, 523.25, 659.25]:  # A4, C5, E5
        wave = generate_sine_wave(freq, 0.1, sample_rate)
        # 应用淡入淡出效果
        fade_samples = int(0.03 * sample_rate)
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        wave[:fade_samples] *= fade_in
        wave[-fade_samples:] *= fade_out
        waves.append(wave)
        total_duration += 0.1
    
    # 结尾音符
    final_freq = 783.99  # G5
    final_duration = 0.2
    final_wave = generate_sine_wave(final_freq, final_duration, sample_rate)
    # 应用淡入淡出效果
    fade_samples = int(0.05 * sample_rate)
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    final_wave[:fade_samples] *= fade_in
    final_wave[-fade_samples:] *= fade_out
    waves.append(final_wave)
    
    # 合并所有波形
    combined_wave = np.concatenate(waves)
    
    # 归一化到 [-1, 1] 范围
    combined_wave = combined_wave / np.max(np.abs(combined_wave))
    
    # 转换为16位整数
    combined_wave = (combined_wave * 32767).astype(np.int16)
    
    # 保存为WAV文件
    wavfile.write(sounds_dir / 'achievement.wav', sample_rate, combined_wave)
    print(f"已生成achievement音效: {sounds_dir / 'achievement.wav'}")

def generate_levelup_sound():
    """生成levelup音效 - 上升的音阶和持续的高音"""
    sample_rate = 44100
    total_duration = 0
    waves = []
    
    # 上升的音阶
    for freq in [392.00, 493.88, 587.33]:  # G4, B4, D5
        wave = generate_sine_wave(freq, 0.12, sample_rate)
        # 应用淡入淡出效果
        fade_samples = int(0.04 * sample_rate)
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        wave[:fade_samples] *= fade_in
        wave[-fade_samples:] *= fade_out
        waves.append(wave)
        total_duration += 0.12
    
    # 持续的高音
    final_freq = 783.99  # G5
    final_duration = 0.25
    final_wave = generate_sine_wave(final_freq, final_duration, sample_rate)
    # 应用淡入淡出效果
    fade_samples = int(0.08 * sample_rate)
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    final_wave[:fade_samples] *= fade_in
    final_wave[-fade_samples:] *= fade_out
    waves.append(final_wave)
    
    # 合并所有波形
    combined_wave = np.concatenate(waves)
    
    # 归一化到 [-1, 1] 范围
    combined_wave = combined_wave / np.max(np.abs(combined_wave))
    
    # 转换为16位整数
    combined_wave = (combined_wave * 32767).astype(np.int16)
    
    # 保存为WAV文件
    wavfile.write(sounds_dir / 'levelup.wav', sample_rate, combined_wave)
    print(f"已生成levelup音效: {sounds_dir / 'levelup.wav'}")

def generate_success_sound():
    """生成success音效 - 简单的上升和弦"""
    sample_rate = 44100
    
    # 创建两个音符的和弦
    freq1 = 523.25  # C5
    freq2 = 659.25  # E5
    duration = 0.5
    
    wave1 = generate_sine_wave(freq1, duration, sample_rate)
    wave2 = generate_sine_wave(freq2, duration, sample_rate)
    
    # 合并波形
    combined_wave = (wave1 + wave2) / 2
    
    # 应用淡入淡出效果
    fade_samples = int(0.1 * sample_rate)
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    combined_wave[:fade_samples] *= fade_in
    combined_wave[-fade_samples:] *= fade_out
    
    # 归一化到 [-1, 1] 范围
    combined_wave = combined_wave / np.max(np.abs(combined_wave))
    
    # 转换为16位整数
    combined_wave = (combined_wave * 32767).astype(np.int16)
    
    # 保存为WAV文件
    wavfile.write(sounds_dir / 'success.wav', sample_rate, combined_wave)
    print(f"已生成success音效: {sounds_dir / 'success.wav'}")

if __name__ == "__main__":
    print("开始生成音效文件...")
    generate_bingo_sound()
    generate_achievement_sound()
    generate_levelup_sound()
    generate_success_sound()
    print("所有音效文件生成完成！") 