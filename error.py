# error module classes

class NotMatrixServerError(RuntimeError):
    """The server is not a matrix server"""
    
    pass

class MatrixError(RuntimeError):
    """wraps a Matrix api erro"""
    
    def __init__(self, code, body):
        self.code = code
        self.body = body
        