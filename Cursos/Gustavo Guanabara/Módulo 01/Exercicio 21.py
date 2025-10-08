#Este programa reproduz uma musica no formato .mp3
import pygame

pygame.mixer.init()
pygame.mixer.music.load('Exercicio 21.mp3')
pygame.mixer.music.play()
input('Pressione Enter para encerrar a música...')

