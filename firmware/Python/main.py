# импорт библиотек
import cv2
from paho.mqtt.client import Client
from threading import Thread
import time

# данные для подключения к mqtt брокеру
hostname = 'mqtt.pi40.ru'
port = 1883
username = 'danisimo'
password = '1234567890'
topic = 'danisimo'

# список заказов
orders = []

#хранение сентров аруко марок
centers_mark = dict()

# переменные для установки паузы на островах и магазине
pause = False
pause_timer = 0

# настройка mqtt клиента
def connect_status(device, userdata, flags, result):
    print(f'Устройство подключено {result}')

def subscribe_status(device, userdata, mid, qos):
    print(f'Устройство подписано {mid}')
    
def messages(device, userdata, message):
    # при первом заказе, система фиксирует (сохраняет) центры островов и магазина для дальнейшей работы.
    if orders == [] and (message.topic == f'{topic}/island1' or message.topic == f'{topic}/island2'):
        global centers_mark_fix
        centers_mark_fix = centers_mark.copy()

    # обработка заказов
    if message.topic == f'{topic}/island1':
        if orders == []:
            orders.append(['Island1', message.payload.decode(), 'go'])
            device.publish(f'{topic}/status1', 'o1. В пути')
        else:
            orders.append(['Island1', message.payload.decode(), 'add'])
    elif message.topic == f'{topic}/island2':
        if orders == []:
            orders.append(['Island2', message.payload.decode(), 'go'])
            device.publish(f'{topic}/status1', 'o2. В пути')
        else:
            orders.append(['Island2', message.payload.decode(), 'add'])
    
device = Client('python_test')
device.username_pw_set(username, password)
device.connect(hostname, port)
device.on_connect = connect_status
device.subscribe(f'{topic}/island1')
device.subscribe(f'{topic}/island2')
device.on_subscribe = subscribe_status
device.on_message = messages
# помещаем бесконечный цикл обработки mqtt слиента в отдельный поток для корректнной работы комп.зрения и mqtt
th = Thread(target=device.loop_forever)
th.start()


cap = cv2.VideoCapture(0)
key = -1
dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)

# цикл видеопотока
while key == -1:
    _, image = cap.read()
    
    #детект аруко меток
    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    corners_all, ids, _ = cv2.aruco.detectMarkers(image_gray, dictionary)
    #cv2.aruco.drawDetectedMarkers(image, corners_all)

    # вывод текущих заказов на экран
    y0, dy = 20, 20
    t = [' '.join(o) for o in orders]
    for i, line in enumerate(t):
        y = y0 + i*dy
        cv2.putText(image, line, (0, y), cv2.FONT_HERSHEY_COMPLEX, 0.5, (0, 255, 0), 1)
    
    # перебор всех координат угол аруко меток для дальнейших приколюх
    for i, corners_marker in enumerate(corners_all):
        for corner in corners_marker:
            #левый верхний
            x1, y1 = int(corner[0][0]), int(corner[0][1])
    
            # правый нижний
            x3, y3 = int(corner[2][0]), int(corner[2][1])

            # находим центр
            xc = int((x1 + x3) / 2)
            yc = int((y1 + y3) / 2)
            
            # по id определяем к кому какие координаты принадлежат и выводим на экран в виде оточек
            if ids[i][0] == 1:
                centers_mark['Rover'] = (x1, y1)
                cv2.putText(image, 'WRC', (int(xc), int(yc)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.circle(image, (int(xc), int(yc)), 5, (255, 0, 0), -1)
            elif ids[i][0] == 2:
                centers_mark['Shop'] = (xc, yc)
                cv2.circle(image, (int(xc), int(yc)), 5, (255, 0, 0), -1)
                cv2.putText(image, 'Shop', (int(xc), int(yc)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            elif ids[i][0] == 3:
                centers_mark['Island1'] = (xc, yc)
                cv2.circle(image, (int(xc), int(yc)), 5, (255, 0, 0), -1)
                cv2.putText(image, 'Island1', (int(xc), int(yc)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            elif ids[i][0] == 4:
                centers_mark['Island2'] = (xc, yc)
                cv2.circle(image, (int(xc), int(yc)), 5, (255, 0, 0), -1)
                cv2.putText(image, 'Island2', (int(xc), int(yc)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
    # тут вообще жескач начинается. Это имитация остановки у острова или магазина на 5 сек и отравки статуса
    if pause:
        device.publish(f'danisimo/move', '5')
        if time.time() - pause_timer > 5:
            if orders[0][0] == 'Island1':
                if orders[0][2] == 'done':
                    device.publish(f'danisimo/status1', '')
                else:
                    device.publish(f'danisimo/status1', 'o1. В пути')
            
            elif  orders[0][0] == 'Island2':
                if orders[0][2] == 'done':
                    device.publish(f'danisimo/status1', '')
                else:
                    device.publish(f'danisimo/status1', 'o2. В пути')
            pause = False

    # магия связанная с путешествием от магаза до острова и обратно
    if orders != [] and pause == False:
        # try надо для отлавливаем ошибок, лень условия проверок делать
        try:
            order = orders[0]
            # если заказ до острова номер один
            if order[0] == "Island1":
                # условия если робот едет до острова
                if order[2] == 'go':
                    # рисуем центры и прямую линию маршрута от ровера до острова
                    cv2.circle(image, centers_mark_fix['Shop'], 5, (0, 0, 255), -1)
                    cv2.circle(image, centers_mark_fix['Rover'], 5, (0, 0, 255), -1)
                    cv2.circle(image, centers_mark_fix['Island1'], 5, (0, 0, 255), -1)
                    cv2.line(image, centers_mark_fix['Rover'], centers_mark_fix['Island1'], (255, 51, 255), 1)

                    # рисуем некую область возле островов 
                    _x, _y = centers_mark_fix['Island1']
                    pt1_x, pt1_y = _x - 50, _y - 50
                    pt2_x, pt2_y = _x + 50, _y + 50
                    cv2.rectangle(image, (pt1_x, pt1_y), (pt2_x, pt2_y), (255, 0, 0), 1)
                    
                    # если ровер заехал в эту область, останавливаемся, меняем статусы, меняем траекторию Остров-магаз
                    if (pt1_x <= centers_mark['Rover'][0] <= pt2_x) and (pt1_y <= centers_mark['Rover'][1] <= pt2_y):
                        device.publish(f'danisimo/move', '5')
                        device.publish(f'danisimo/status1', 'o1. Доставленно')
                        order[2] = 'done'
                        centers_mark_fix['Rover'] = centers_mark['Rover']
                        pause = True
                        pause_timer = time.time()

                    # езда по линии. Алгоритм определяет, точка метки вверху или снизу прямой и определяет насколько далеко
                    D = (centers_mark['Rover'][0] - centers_mark_fix['Island1'][0]) * (centers_mark_fix['Rover'][1] - centers_mark_fix['Island1'][1]) - (centers_mark['Rover'][1] - centers_mark_fix['Island1'][1]) * (centers_mark_fix['Rover'][0] - centers_mark_fix['Island1'][0])
                    # если робоб слева от линии, подается команда роботу на включение левого мотора, правый офф 
                    if D <= 0:
                        device.publish(f'danisimo/move', '4')
                    # если робоб справа от линии, подается команда роботу на включение правого мотора, левый офф
                    elif D >= 0:
                        device.publish(f'danisimo/move', '3')
                
                # если робот доехал до острова, начинаем ехать в магаз 
                elif order[2] == 'done':
                    # рисуем центры и прямую линию маршрута от ровера до острова
                    cv2.circle(image, centers_mark_fix['Shop'], 5, (0, 0, 255), -1)
                    cv2.circle(image, centers_mark_fix['Rover'], 5, (0, 0, 255), -1)
                    cv2.circle(image, centers_mark_fix['Island1'], 5, (0, 0, 255), -1)
                    cv2.line(image, centers_mark_fix['Rover'], centers_mark_fix['Shop'], (255, 51, 255), 1)
                    
                    # рисуем некую область возле островов
                    _x, _y = centers_mark_fix['Shop']
                    pt1_x, pt1_y = _x - 50, _y - 50
                    pt2_x, pt2_y = _x + 50, _y + 50
                    cv2.rectangle(image, (pt1_x, pt1_y), (pt2_x, pt2_y), (255, 0, 0), 1)
                    
                    # если ровер заехал в эту область, останавливаемся, меняем статусы, меняем траекторию Магаз-остров
                    if (pt1_x <= centers_mark['Rover'][0] <= pt2_x) and (pt1_y <= centers_mark['Rover'][1] <= pt2_y):
                        device.publish(f'danisimo/move', '5')
                        if len(orders) > 1:
                            if orders[1][0] == 'Island1':
                                device.publish(f'danisimo/status1', 'o1. Собираем')
                            elif orders[1][0] == 'Island2':
                                device.publish(f'danisimo/status1', 'o2. Собираем')
                        else:
                            device.publish(f'danisimo/status1', '')

                        orders.pop(0)
                        orders[0][2] = 'go'
                        centers_mark_fix['Rover'] = centers_mark['Rover']
                        pause = True
                        pause_timer = time.time()

                    # езда по линии. Алгоритм определяет, точка метки вверху или снизу прямой и определяет наскольк далеко
                    D = (centers_mark['Rover'][0] - centers_mark_fix['Shop'][0]) * (centers_mark_fix['Rover'][1] - centers_mark_fix['Shop'][1]) - (centers_mark['Rover'][1] - centers_mark_fix['Shop'][1]) * (centers_mark_fix['Rover'][0] - centers_mark_fix['Shop'][0])
                    
                    # если робоб слева от линии, подается команда роботу на включение левого мотора, правый офф
                    if D <= 0:
                        device.publish(f'danisimo/move', '4')
                    # если робоб справа от линии, подается команда роботу на включение правого мотора, левый офф
                    elif D >= 0:
                        device.publish(f'danisimo/move', '3')
            
            # все тоже самое как и у острова 1. Да хардкод, но нужно было быстро делать
            elif order[0] == "Island2":
                if order[2] == 'go':
                    cv2.circle(image, centers_mark_fix['Shop'], 5, (0, 0, 255), -1)
                    cv2.circle(image, centers_mark_fix['Rover'], 5, (0, 0, 255), -1)
                    cv2.circle(image, centers_mark_fix['Island2'], 5, (0, 0, 255), -1)
                    cv2.line(image, centers_mark_fix['Rover'], centers_mark_fix['Island2'], (255, 51, 255), 1)

                    _x, _y = centers_mark_fix['Island2']
                    pt1_x, pt1_y = _x - 50, _y - 50
                    pt2_x, pt2_y = _x + 50, _y + 50
                    cv2.rectangle(image, (pt1_x, pt1_y), (pt2_x, pt2_y), (255, 0, 0), 1)
                    if (pt1_x <= centers_mark['Rover'][0] <= pt2_x) and (pt1_y <= centers_mark['Rover'][1] <= pt2_y):
                        device.publish(f'danisimo/move', '5')
                        device.publish(f'danisimo/status1', 'o2. Доставленно')
                        order[2] = 'done'
                        centers_mark_fix['Rover'] = centers_mark['Rover']
                        pause = True
                        pause_timer = time.time()

                    D = (centers_mark['Rover'][0] - centers_mark_fix['Island2'][0]) * (centers_mark_fix['Rover'][1] - centers_mark_fix['Island2'][1]) - (centers_mark['Rover'][1] - centers_mark_fix['Island2'][1]) * (centers_mark_fix['Rover'][0] - centers_mark_fix['Island2'][0])
                    if D <= 0:
                        device.publish(f'danisimo/move', '4')
                    elif D >= 0:
                        device.publish(f'danisimo/move', '3')
                
                elif order[2] == 'done':
                    cv2.circle(image, centers_mark_fix['Shop'], 5, (0, 0, 255), -1)
                    cv2.circle(image, centers_mark_fix['Rover'], 5, (0, 0, 255), -1)
                    cv2.circle(image, centers_mark_fix['Island2'], 5, (0, 0, 255), -1)
                    cv2.line(image, centers_mark_fix['Rover'], centers_mark_fix['Shop'], (255, 51, 255), 1)

                    _x, _y = centers_mark_fix['Shop']
                    pt1_x, pt1_y = _x - 50, _y - 50
                    pt2_x, pt2_y = _x + 50, _y + 50
                    cv2.rectangle(image, (pt1_x, pt1_y), (pt2_x, pt2_y), (255, 0, 0), 1)
                    if (pt1_x <= centers_mark['Rover'][0] <= pt2_x) and (pt1_y <= centers_mark['Rover'][1] <= pt2_y):
                        device.publish(f'danisimo/move', '5')

                        if len(orders) > 1:
                            if orders[1][0] == 'Island1':
                                device.publish(f'danisimo/status1', 'o1. Собираем')
                            elif orders[1][0] == 'Island2':
                                device.publish(f'danisimo/status1', 'o2. Собираем')
                        else:
                            device.publish(f'danisimo/status1', '')
                        orders.pop(0)
                        orders[0][2] = 'go'
                        centers_mark_fix['Rover'] = centers_mark['Rover']
                        pause = True
                        pause_timer = time.time()

                    D = (centers_mark['Rover'][0] - centers_mark_fix['Shop'][0]) * (centers_mark_fix['Rover'][1] - centers_mark_fix['Shop'][1]) - (centers_mark['Rover'][1] - centers_mark_fix['Shop'][1]) * (centers_mark_fix['Rover'][0] - centers_mark_fix['Shop'][0])
                    if D <= 0:
                        device.publish(f'danisimo/move', '4')
                    elif D >= 0:
                        device.publish(f'danisimo/move', '3')
        except Exception as e:
                print(e)
    # отображение на экране изображение в 1.5 раза делаем больше для удобства        
    image = cv2.resize(image,(int(image.shape[1]* 1.5), int(image.shape[0]* 1.5)))
    cv2.imshow('Water robot courier', image)
    key = cv2.waitKey(20)                 
# отключаемся от mqtt
device.disconnect()
# освобождение ресурса устройства камеры
cap.release()


