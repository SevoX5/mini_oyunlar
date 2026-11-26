import oyun_merkezi
import traceback

print("1 - Dosya yüklendi")

try:
    print("2 - Uygulama oluşturuluyor")
    uygulama = oyun_merkezi.Uygulama()
    print("3 - Uygulama oluşturuldu")

    while True:
        print("4 - Döngü çalışıyor")
        gecen = min(oyun_merkezi.saat.tick(oyun_merkezi.KARE_HIZI) / 1000, 0.033)

        for olay in oyun_merkezi.pygame.event.get():
            print("OLAY:", olay)
            uygulama.olay_isle(olay)

        uygulama.adim(gecen)
        oyun_merkezi.pygame.display.flip()

except BaseException:
    traceback.print_exc()

input("Test bitti. Enter'a bas...")