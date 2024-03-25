import select
import socket
import logging
import signal
import time

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self.sigterm_received = False

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        signal.signal(signal.SIGTERM, self.__sigterm_handler)
        
        while not self.sigterm_received:
            client_sock = self.__accept_new_connection(timeout=0.1)
            if client_sock is not None:
                self.__handle_client_connection(client_sock)
        self._server_socket.close()
        logging.info("action: closing_server_socket | result: success")
        logging.info(f"action: sigterm_signal_handling | result: success")
        logging.info("action: server_shutdown | result: success")
        
    def __sigterm_handler(self, signum, frame):
        """
        Signal handler for SIGTERM to gracefully shutdown the server

        This function will be called when the server receives a SIGTERM
        signal. The server will set the sigterm_received flag to True and
        will stop accepting new connections.
        """

        self.sigterm_received = True
        logging.info(f"action: sigterm_signal_handling | result: in_progress")

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            # TODO: Modify the receive to avoid short-reads
            msg = client_sock.recv(1024).rstrip().decode('utf-8')
            addr = client_sock.getpeername()
            logging.info(f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}')
            # TODO: Modify the send to avoid short-writes
            client_sock.send("{}\n".format(msg).encode('utf-8'))
        except OSError as e:
            logging.error("action: receive_message | result: fail | error: {e}")
        finally:
            client_sock.close()

    def __accept_new_connection(self, timeout):
        """
        Accept new connections with a timeout

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        But if timeout is reached, None is returned and it means
        that either no client connected or a SIGTERM signal was received
        """

        start_time = time.time()
        while time.time() - start_time < timeout:
            logging.info('action: accept_connections | result: in_progress')
            ready, _, _ = select.select([self._server_socket], [], [], timeout)
            if ready: # Verifies if the server socket is ready to be read, avoiding a blocking call
                c, addr = self._server_socket.accept()
                logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
                return c
            if self.sigterm_received:
                break
        logging.info('action: accept_connections | result: timeout_exceeded')
        return None
