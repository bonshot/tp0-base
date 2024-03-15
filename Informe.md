# <span style="color:#3d24c9">TP0: Docker, concurrencia y comunicación</span>
Bienvenidos a mi TP0 de Sistemas Distribuidos, soy Facundo Aguirre Argerich.  
En este trabajo práctico vamos a trabajar con Docker, concurrencia y comunicación entre procesos.

## <span style="color:#9669f0">Ejercicio 1 y 1.1</span>
Para el ejercicio 1 simplemente basta con agregar una configuración similar al `client1` proporcionado por la cátedra para poder tener un `container` nuevo que se conecte al server, a fin de cuentas usará la misma red.    

De manera análoga en el ejercicio 1.1 solo debemos agregar las líneas mencionadas cambiando el ID del cliente de forma que se identifique de forma única en la red. Esto decidí hacerlo con bash por simplicidad en el manejo de archivos y esto nos ahorra, como se explicó en la presentación del trabajo, tener que hacer a mano tantos clientes nuevos como queramos.  
La forma de ejecutar el script es la siguiente:  
```bash
./create_clients.sh <cantidad_de_clientes>
```
O para entornos no unix-like:
```bash
bash create_clients.sh <cantidad_de_clientes>
```  
Luego de ejecutarlo se generará un archivo `docker-compose.yml` con la cantidad de clientes que se haya especificado integrados en la red del server. Se hizo esto con el solo fin de no interferir con el `docker-compose-dev.yml` que provee la cátedra, es meramente arbitrario. 
Para poder "uppear" los contenedores se reemplaza en el `Makefile` proveído por la cátedra el `docker-compose-dev.yml` por el generado por el script.  

## <span style="color:#9669f0">Ejercicio 2</span>
En este ejercicio se quiere poder separar la configuración del container de la aplicación en sí. Para eso vamos a usar docker volumes para poder montar un archivo config tanto de `server` como de `client` y que estos puedan leerlo, evitando que tengamos que recompilar la imagen completa al cambiar algo en estas configs.  
1. Creo un volumen usando el comando `docker volume create config-volume`.
2. Utilizo para la ejecución de los containers, el comando `docker run --rm -v $(PWD)/server/config.ini:/config2/config.ini -v config-volume:/config alpine cp /config2/config.ini /config`. Primero que nada con lo que está después del primer -v monto el archivo `config.ini` en el directorio `/config` del container, y con el segundo -v monto el volumen `config-volume` que es el que ya cree de manera externa en la consola, para luego poder usar el container temporal donde guardé el archivo `config.ini` para copiarlo al volumen `config-volume` usando alpine como herramienta. Esto se hace de manera análoga con el cliente. Estos comandos fueron definidos en el `Makefile` para poder ejecutarlos de manera más sencilla al usar el comando make _docker-compose-up_.  
Dicho comando solo se ejecutará para copiar las configs inicialmente, porque en caso de que lo haga cada vez que se haga `docker-compose up` se sobreescribirán las configs con las originales. Para eso agregué el siguiente if en el script `copy-checker.sh` usando `bash`:
```makefile
if ! docker run --rm -v config-volume:/config alpine test -e /config/config.x
```  
Que comprueba si el archivo `config.x` ya existe en el volumen `config-volume` y si no lo copia.      
3. Una vez con los archivos de configuración en mi volumen tengo que modificar el docker-compose para que los containers utilicen el volumen. Para esto simplemente agrego la siguiente línea en el `docker-compose.yml` para los servicios `server` y `client` respectivamente:
```yaml
volumes:
  - config-volume:/config
```
Sin olvidarme claro de agregar esto a la definición de mi script para poder crear múltiples clientes, agregando la especificación del volúmen que estoy usando tanto en servidor como cliente y declaralo como externo (ya que lo cree de manera externa con el comando `docker create`).

